# Hardware and software evidence

Test phone: **iPhone18,2, iOS 26.4**. On-device upstream base:
`395c4d5a0b5960536c22564f948049122383f3fb` (StikDebug 3.2.1), with local patches.

## Physical observations

| Route / step | Result | Evidence |
| --- | --- | --- |
| Mac over USB: set location | Passed, October 26 | Developer command accepted; user confirmed Apple Maps blue dot |
| Mac over USB: restore | Passed, October 26 | User confirmed real location in Maps |
| On-device: free signing, install, Trust, protected pairing import | Passed, November 7 | Same bundle ID; private phone pairing file mode 600, backup excluded; shared copy removed |
| Earlier on-device candidate: set location | Passed | Apple Park blue dot confirmed in Maps |
| Earlier candidate: unplugged locked persistence | **Failed after 10m20s** | Maps returned to the real location before StikDebug was reopened |
| Earlier candidate: explicit restore | Passed | Command accepted without USB; real Maps blue dot confirmed |
| Developer-heartbeat experiment | Unavailable | Diagnostic connection closed; no second lock timer started |
| Final background-activity candidate: session readiness | Passed | User confirmed both “Location updates active” and “Background location session ready” |
| Final candidate: Maps baseline | Passed | Apple Park current-location blue dot confirmed |
| Final candidate: unplugged locked persistence | **Passed after 10m28s** | USB absent in Mac registry at both boundaries; no phone/debugger calls; Maps inspected first |
| Final candidate: Restore Real GPS | **Passed with USB unplugged** | User reported restore worked, then separately confirmed real-location Maps blue dot |

The final locked interval ran on November 7, 2026, from **08:33:24 to 08:43:52
UTC** (628 seconds). Post-lock Maps confirmation was recorded at 08:44:38 UTC;
separate real-GPS Maps confirmation was recorded at 08:55:51 UTC.

These are user-observed Maps results. No real-location coordinates, pairing
contents, account information, or device serial number are included. Structured
observations are in [`compat/results.json`](../compat/results.json).

One passing locked interval does not establish overnight reliability, survival
after OS termination or reboot, VPN recovery, or behavior after profile expiry.
The first failure does not prove an OS kill; suspension, VPN loss and developer
connection loss were not distinguished.

## Software validation

- Original backend baseline: 40 passing mock-device tests. These cover discovery,
  readiness, coordinate validation, reuse, restore, loss/reconnection behavior,
  bounded retry, timeout, concurrency, graceful shutdown and localhost controls.
- On-device source: signed iPhoneOS Debug build passed with Xcode 27.2.
- Session safety harness: eight checks passed using the actual session source
  with device/audio stubs; this preceded the final Core Location API change.
- Expiry parser: five checks passed with synthetic profiles.
- A final candidate passed the physical sequence above. Mock tests are not
  physical-device evidence.
- Publication-time checks are recorded in [`VALIDATION.md`](VALIDATION.md).

## Still unverified

Location Probe was not installed on this phone, so no
`CLLocationSourceInformation.isSimulatedBySoftware` reading was obtained.
Other-app compatibility, overnight operation, Wi-Fi pairing, and Raspberry
Pi/Linux deployment are unverified. No attendance or clock-in testing occurred.
