# Troubleshooting
| Symptom / code | Fix |
|---|---|
| `device_not_found` | Cable, unlock phone, tap Trust. `pymobiledevice3 usbmux list` should show it. |
| `not_paired` | Unlock and accept the Trust prompt, enter passcode. |
| `developer_mode_disabled` | Settings → Privacy & Security → Developer Mode. Restart, confirm. (Observed on the test phone.) |
| `developer_image_missing` | "Mount developer image" button or `pymobiledevice3 mounter auto-mount` (internet required). |
| `unsupported_ios_version` | Needs iOS 17.4+ (userspace tunnel requires CoreDeviceProxy). |
| `tunnel_failed` / `service_timeout` | Unlock phone, replug, retry. Close Xcode/Finder sync that may hold the device. |
| `multiple_devices` | Choose the iPhone in the dropdown. |
| State `LOST` | Cable/connection dropped. Press Set Location again; nothing is re-applied automatically. |
| Location stays after Restore | Verify in Location Probe (`isSimulatedBySoftware`). Reboot the phone if needed. |
Logs: `~/.anywhere-gps/logs/backend.jsonl`; crashes: `~/.anywhere-gps/crash/`.
