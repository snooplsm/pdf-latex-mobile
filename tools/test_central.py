from pathlib import Path
import tempfile
import unittest
from central import read_credentials

class CredentialTests(unittest.TestCase):
    def test_server_fragment_and_namespaced_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.xml'
            fragment = '<server><id>central</id><username>test-user</username><password>test-token</password></server>'
            for xml in (fragment, '<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"><servers>' + fragment + '</servers></settings>'):
                path.write_text(xml)
                path.chmod(0o600)
                self.assertEqual(read_credentials(path, 'central'), {'username': 'test-user', 'password': 'test-token'})
                with self.assertRaises(ValueError):
                    read_credentials(path, 'missing')

    def test_rejects_public_file_and_placeholders(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.xml'
            path.write_text('<server><username>${env.TOKEN}</username><password>test-token</password></server>')
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                read_credentials(path)
            path.chmod(0o600)
            with self.assertRaises(ValueError):
                read_credentials(path)
