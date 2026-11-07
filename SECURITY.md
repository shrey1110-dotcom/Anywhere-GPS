# Reporting a security issue

Do not open a public issue containing credentials, pairing data, provisioning
profiles, device identifiers or raw protocol logs. Use GitHub's private security
reporting interface if it is enabled for this repository. If it is unavailable,
ask the maintainer for a private channel without posting sensitive details.

Restore real GPS and close the developer session when testing is finished.
For a suspected credential disclosure, stop sharing the file and use Apple's
device trust controls to revoke the affected relationship. Never post the
credential as part of a reproduction.

The project is experimental and has no formal security-audit claim. See
[`docs/PRIVACY.md`](docs/PRIVACY.md) and
[`ondevice/PROVENANCE.md`](ondevice/PROVENANCE.md) for the review limits.
