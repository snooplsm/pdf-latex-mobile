# Release signing key

Public OpenPGP key for LaTeX Mobile Maven releases: [release-signing.asc](release-signing.asc).

Fingerprint: `0238608727F998F5C55B96E746B7A1A222D25A1D`

```sh
gpg --import keys/release-signing.asc
gpg --fingerprint 0238608727F998F5C55B96E746B7A1A222D25A1D
gpg --verify latex-mobile-balanced-0.1.0.aar.asc latex-mobile-balanced-0.1.0.aar
```

Confirm the fingerprint against a trusted release announcement before relying on a signature.
