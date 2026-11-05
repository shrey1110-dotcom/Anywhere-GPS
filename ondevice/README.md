# Reproduce the local StikDebug changes

This is a source-only patch set for the independent
[StikDebug repository](https://github.com/StikDebug/StikDebug), pinned to
`395c4d5a0b5960536c22564f948049122383f3fb` (3.2.1). It does not contain a signed
app, a pairing record, a signing identity, or the bundled native archive.

The 19 patches include private pairing storage, explicit restore and cancellation,
accurate location-session status, expiry warnings, free-signing entitlement
adjustments, and the final `CLBackgroundActivitySession` candidate. Optional
debug diagnostics remain opt-in and do not export credential values.

## Build from source

For a new development checkout, obtain only the official upstream:

```bash
git clone https://github.com/StikDebug/StikDebug.git StikDebug-personal
cd StikDebug-personal
git checkout --detach 395c4d5a0b5960536c22564f948049122383f3fb
# Read AGENTS.md before contributing.
cd ../Anywhere-GPS
./ondevice/apply.sh ../StikDebug-personal
```

The apply script requires a clean pinned checkout and checks the patch set before
changing it. Do not run it over an existing modified/personal installation tree.
The owner's original audit checkout is intentionally left untouched.

1. Open `StikDebug.xcodeproj` in Xcode. The tested environment used Xcode 27.2.
2. Select your own free **Personal Team** in Apple's Xcode UI. The patch contains
   no personal team selection. Retain your existing bundle ID when renewing an
   installed build; do not delete the app or churn IDs.
3. Resolve the versions in `Package.resolved`; do not substitute dependencies.
4. Build and install through Xcode. Complete Trust/Developer Mode prompts directly
   on your phone. No Apple credentials belong in StikDebug or this repository.
5. Install/configure LocalDevVPN using the documented upstream flow, then follow
   [`docs/ON_DEVICE.md`](../docs/ON_DEVICE.md).

The original personal build uses the bundle ID recorded in its source. For a
different owner's first installation, configure their own unique ID and make
the local exporter's `BUNDLE_ID` match. This is not an instruction to change the
existing tested phone's ID.

## Pairing

The exporter in `scripts/export_stikdebug_pairing.py` is designed for the tested
local environment and installed personal bundle. Read it before use. Run with
the existing virtual environment, only after installing the app and approving
USB trust. It generates a device credential; do not run it just to inspect a repo.

Keep credentials only on Mac and phone, mode 600 in a private parent directory.
Transfer directly over USB; never upload or paste them. The phone patch imports
into protected Application Support storage and removes the shared staging copy.
The tested existing phone already has its credential; routine reinstall/renewal
does not require generating another.

## Scope

Patch application and source equivalence were checked locally. The final original
build was signed, installed, and tested in Maps, including one unplugged locked
10m28s interval and explicit restore. The public patch set omits personal signing
selection and is not itself a newly signed or separately hardware-tested binary.
See [PROVENANCE.md](PROVENANCE.md), [manifest.json](manifest.json), and the
[hardware report](../docs/TEST_RESULTS.md).

Before upstream submission, comply with the retained
[contribution rules](UPSTREAM_CONTRIBUTION_RULES.md). No upstream PR is submitted
by this publication, and no human source-review claim is made.
