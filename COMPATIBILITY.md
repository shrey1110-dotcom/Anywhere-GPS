# Compatibility

Tested device: **iPhone18,2 / iOS 26.4**. Mac library: pymobiledevice3 **11.45.0**.
The Mac route supports iOS 17.4+ via a no-root userspace tunnel; on-device
observations apply only to the tested model/iOS and patched build.

| App / check | Status |
| --- | --- |
| Apple Maps location UI | Observed: set location and real-GPS restoration |
| Final on-device candidate: locked persistence | **Passed one 10m28s USB-disconnected interval** |
| Final candidate: explicit restore with USB unplugged | **Passed**, including separate real-location blue-dot confirmation |
| Earlier candidate: locked persistence | **Failed after 10m20s**; subsequent restore passed |
| Other apps | `not_tested`; no compatibility claim |
| Location Probe source information | Not obtained on the phone |

Structured observations in [`compat/results.json`](compat/results.json) are
validated by `compatibility_report.py` and exposed by `GET /api/compatibility`.
The [hardware report](docs/TEST_RESULTS.md) distinguishes command acceptance,
Maps observations, and source-information verification.

Overnight operation, process termination, reboot, VPN loss and signing expiry
are unverified. A Maps blue dot does not establish another app's behavior or
hide software simulation. Attendance/clock-in falsification, geofence fraud
and integrity-check bypass are outside scope; no such testing was performed.
