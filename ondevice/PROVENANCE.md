# Source and audit limits

- Upstream: `https://github.com/StikDebug/StikDebug.git`
- Base revision: `395c4d5a0b5960536c22564f948049122383f3fb` (3.2.1)
- The patches contain the local source changes and three added Swift helpers.
  Personal signing team selection is deliberately omitted.
- `manifest.json` records each patch's source path and SHA-256.
- Upstream licensing and contribution rules are retained alongside the patches.

The pinned source bundles `StikDebug/idevice/libidevice_ffi.a`; upstream does not
build this archive from reviewed native source in this checkout. It is not
redistributed by Anywhere GPS. The inspected pinned archive's SHA-256 was
`4db23fe1d342927b9480bb9a8577f219994365621dc28aa0018e23ea1990ecc8`.
The inspected header's SHA-256 was
`696286794e8cf1c18a91d4dab5046cef4d9bae352f5e7a1ad33fbc0ba30d7ab4`.
These identify bytes, not a reproducible native-source build or a security audit.

Swift package pins: CodeEditorView **0.15.4** at
`aba6c189bb2f6fd9d7b8e9f5739aeb3c8c7e3254`; Rearrange **1.8.1** at
`5ff7f3363f7a08f77e0d761e38e6add31c2136e1`. Local source searches found no
network/login/telemetry API calls in their Sources directories. That limited
search is not a complete dependency audit.

External research for the local review was restricted to the official StikDebug
repository and `docs.sidestore.io`; Apple's installed SDK headers were inspected
locally for the background API. LocalDevVPN's separate binary/source/privacy
policy was not fully audited. Avoid claims of complete privacy clearance.

The original and failed experiments remain described in the hardware report.
No upstream submission, credential upload, or paid signing occurred.
