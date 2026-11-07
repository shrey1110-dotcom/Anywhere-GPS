# Architecture

```
React+Leaflet UI ──HTTP(127.0.0.1)──> FastAPI (app.py) ──> SessionManager ──> Services{discovery,setup,simulator}
                                                                               ├─ real: pymobiledevice3 (usbmux, lockdown, userspace RSD tunnel, DVT)
                                                                               └─ mock: MockFarm (tests / --mock only)
```
| Module | Role |
|---|---|
| `device_discovery.py` | usbmuxd list + lockdown metadata (`autopair=False`: listing never triggers a Trust prompt) |
| `developer_setup.py` | pairing / iOS ≥17.4 / Developer Mode / mounted image → `Readiness` with actionable problems; image mounting |
| `tunnel_manager.py` | no-root in-process `UserspaceRsdTunnel` (needs CoreDeviceProxy, iOS 17.4+) |
| `location_simulator.py` | `DvtProvider` + `LocationSimulation` channel; liveness from DTX connection state |
| `session_manager.py` | per-device state machine IDLE→CONNECTING→ACTIVE→RESTORING / LOST / ERROR, locks, monitor, bounded backoff retries, graceful shutdown |
| `location_restore.py` | compares a Location Probe reading with the old target; the only path to `verified: true` |
| `diagnostics.py`, `compatibility_report.py` | host/version report; evidence-gated compatibility matrix |

## Facts about the library (pymobiledevice3 11.45.0, read from source)
* `dvt simulate-location set` opens tunnel → `DvtProvider` → `LocationSimulation.set()` then **blocks in
  `OSUTILS.wait_return()`**. The process must stay alive; we therefore hold one channel per active session.
* `clear` opens a fresh connection and sends `stopLocationSimulation`. A zero exit code only means the request was
  sent, so the app never says "restored" — it says "command accepted, not yet verified".
* *Unconfirmed on hardware:* that closing the connection ends the simulation (modelled that way in the mock;
  Xcode behaves like this). Treated as unknown until tested with Location Probe.
* Liveness uses private attributes of the DTX connection (`_closed`, `_reader_task`); revisit on library upgrade.

## Safety properties
* Conflicting operations on one device get `409 session_busy` (never queued).
* Device loss → `LOST`, `simulation_active=false`; **never auto-reapplied** after reconnect/reboot.
* Shutdown sends `clear` to active sessions (bounded), then closes channels.
* Crash reports → `~/.anywhere-gps/crash/`, logs (JSON lines) → `~/.anywhere-gps/logs/`.
* No root needed.
