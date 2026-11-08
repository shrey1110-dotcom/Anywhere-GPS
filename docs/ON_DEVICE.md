# On-device operation

Use your own iPhone for harmless map pranks with friends: pick a surprising
location, show it in Maps, then restore real GPS. After initial Mac/Xcode setup,
the on-device flow needs only the iPhone with LocalDevVPN connected. Free
signing lasts up to seven days per profile before renewal on the Mac; this is
not a claim that a simulation was tested continuously for a week.

The phone route uses a local source build of
[StikDebug](https://github.com/StikDebug/StikDebug), a separately installed
LocalDevVPN, and Apple's free Xcode Personal Team. It is separate from the Mac
FastAPI/React app. See [`ondevice/README.md`](../ondevice/README.md) for patches.

## Daily use

1. Connect LocalDevVPN.
2. Open StikDebug, select a location, and tap **Set Location**.
3. Confirm **Location updates active** and **Background location session ready**.
4. Open Maps and check its current-location blue dot.
5. Keep Always location permission, Silent Audio and Background Location enabled.
   Leave StikDebug in the background without swiping it away, and keep VPN connected.
6. When finished, tap **Restore Real GPS**, then confirm the real-location blue dot
   in Maps. A command-accepted message alone is not independent verification.

The final candidate passed one 10m28s locked interval with USB genuinely
disconnected. It uses `CLBackgroundActivitySession`, continuous location updates,
visible background-location indication and session diagnostics. It cannot
promise execution after iOS terminates the process.

After a lost/unknown status, check Maps and use explicit controls. There is no
silent reconnect that reapplies a stale simulated location.

## Free signing

Free Personal Team profiles last seven days, with a maximum of three active
development apps. Use Xcode on the Mac to renew the same app before its actual
embedded-profile expiry. Keep the same bundle ID, install over the existing app,
and preserve the pairing file. A rebuild may reuse an existing profile; verify
the new expiry in the app. No paid developer membership is needed for this flow.

Keep all Apple Account, Keychain, Trust and passcode interaction in Apple's
interfaces. Follow the app's actual expiry warning rather than a date copied
from someone else's device report.

## If persistence becomes unreliable

Use the existing script on a powered USB-connected host:

```bash
# From the repository root; stop the web server first.
.venv/bin/python scripts/set_location.py 37.3349 -122.0090
# Ctrl+C requests restore. Confirm real GPS in Maps.
```

The host must remain powered, awake and connected. The Mac route has physical
test history. Raspberry Pi/Linux deployment has not been performed or verified.
This fallback is not a standalone phone solution.
