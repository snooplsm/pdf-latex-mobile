#!/usr/bin/env python3
"""Build, upload, inspect, and publish a signed Maven Central deployment without CI."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://central.sonatype.com/api/v1/publisher"
VARIANTS = ("tiny", "small", "balanced", "full")


def bundle(version, destination):
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("invalid release version")
    repository = ROOT / "dist/maven"
    files = []
    for variant in VARIANTS:
        artifact = f"latex-mobile-{variant}"
        directory = repository / "io/github/snooplsm" / artifact / version
        for suffix in (".pom", ".aar", "-sources.jar", "-javadoc.jar"):
            file = directory / f"{artifact}-{version}{suffix}"
            signature = Path(str(file) + ".asc")
            if not file.is_file() or not signature.is_file():
                raise ValueError(f"missing artifact/signature: {file}; stage with MAVEN_SIGNING_KEY_FILE set")
            files += [file, signature]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            name = file.relative_to(repository).as_posix()
            data = file.read_bytes()
            archive.writestr(name, data)
            if not file.name.endswith(".asc"):
                for algorithm in ("md5", "sha1", "sha256", "sha512"):
                    archive.writestr(name + "." + algorithm, hashlib.new(algorithm, data).hexdigest())
    return destination


def read_credentials(path, server_id=None):
    if path.stat().st_mode & 0o077:
        raise ValueError("credentials file must be private: chmod 600 FILE")
    if path.suffix == ".xml":
        root = ET.parse(path).getroot()
        servers = [node for node in root.iter() if node.tag.split("}")[-1] == "server"]
        def field(server, name):
            return next(((node.text or "").strip() for node in server if node.tag.split("}")[-1] == name), "")
        if server_id:
            servers = [server for server in servers if field(server, "id") == server_id]
        if len(servers) != 1:
            raise ValueError("Select exactly one Maven server with --server-id")
        credentials = {name: field(servers[0], name) for name in ("username", "password")}
    else:
        credentials = json.loads(path.read_text())
    for name in ("username", "password"):
        value = credentials.get(name, "")
        if not isinstance(value, str) or not value or value.startswith(("${", "{")):
            raise ValueError("Provide a literal Central publisher token; placeholders and Maven-encrypted credentials are not supported")
    return credentials


def request(endpoint, body, content_type, credentials):
    # Credentials stay in memory; never pass them as command-line arguments or print them.
    auth = base64.b64encode(f'{credentials["username"]}:{credentials["password"]}'.encode()).decode()
    req = urllib.request.Request(BASE + endpoint, data=body, method="POST", headers={
        "Authorization": "Bearer " + auth, "Content-Type": content_type,
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            return response.read().decode()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Central returned HTTP {error.code}; response body omitted to protect credentials") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["bundle", "upload", "status", "publish"])
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--credentials", type=Path, default=None)
    parser.add_argument("--server-id", help="Server ID in Maven settings.xml; optional when there is one server")
    parser.add_argument("--deployment")
    args = parser.parse_args()
    path = ROOT / f"dist/central-{args.version}.zip"
    if args.action == "bundle":
        print(bundle(args.version, path))
        return
    settings = Path.home() / ".m2/settings.xml"
    credentials_path = args.credentials or (settings if settings.is_file() else Path.home() / ".config/latex-mobile/central.json")
    credentials = read_credentials(credentials_path, args.server_id)
    if args.action == "upload":
        bundle(args.version, path)
        boundary = "latex-mobile-" + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="bundle"; filename="{path.name}"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n').encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        deployment = request("/upload?" + urllib.parse.urlencode({"name": f"latex-mobile-{args.version}", "publishingType": "USER_MANAGED"}),
                             body, f"multipart/form-data; boundary={boundary}", credentials).strip()
        (ROOT / "dist/central-deployment.json").write_text(json.dumps({"id": deployment, "version": args.version}) + "\n")
        print(deployment)
    else:
        deployment = args.deployment or json.loads((ROOT / "dist/central-deployment.json").read_text())["id"]
        # Validate before interpolating into a URL path.
        deployment = str(uuid.UUID(deployment))
        state = request("/status?" + urllib.parse.urlencode({"id": deployment}), b"", "application/json", credentials)
        if args.action == "status":
            print(state)
        else:
            if json.loads(state)["deploymentState"] != "VALIDATED":
                raise ValueError("deployment must be VALIDATED before publication: " + state)
            print(request("/deployment/" + deployment, b"", "application/json", credentials) or "Publication requested; run status to verify PUBLISHED.")

if __name__ == "__main__":
    main()
