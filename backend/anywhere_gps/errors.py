"""Typed errors. Every error carries a stable code, a user-facing message and an actionable hint."""
from __future__ import annotations


class AnywhereGpsError(Exception):
    code = "internal_error"
    http_status = 500
    hint = ""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if hint is not None:
            self.hint = hint

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "hint": self.hint}


class InvalidCoordinates(AnywhereGpsError):
    code, http_status = "invalid_coordinates", 422
    hint = "Latitude must be within -90..90 and longitude within -180..180."


class DeviceNotFound(AnywhereGpsError):
    code, http_status = "device_not_found", 404
    hint = "Connect the iPhone with a cable, unlock it, and tap Trust if prompted."


class MultipleDevices(AnywhereGpsError):
    code, http_status = "multiple_devices", 409
    hint = "More than one iPhone is connected. Pick one by its UDID."


class NotPaired(AnywhereGpsError):
    code, http_status = "not_paired", 412
    hint = "Unlock the iPhone and tap 'Trust This Computer', then enter the passcode."


class DeveloperModeDisabled(AnywhereGpsError):
    code, http_status = "developer_mode_disabled", 412
    hint = ("Enable Settings > Privacy & Security > Developer Mode on the iPhone "
            "(it appears after the device has been connected to a Mac/Xcode) and restart when asked.")


class DeveloperImageMissing(AnywhereGpsError):
    code, http_status = "developer_image_missing", 412
    hint = "Use 'Mount developer image' in the app (or: pymobiledevice3 mounter auto-mount). Needs internet."


class UnsupportedIOSVersion(AnywhereGpsError):
    code, http_status = "unsupported_ios_version", 412
    hint = "Anywhere GPS supports iOS 17.4 and later (DVT over a no-root userspace RSD tunnel)."


class DeviceUnreachable(AnywhereGpsError):
    code, http_status = "device_unreachable", 503
    hint = "Check the cable, unlock the iPhone, and make sure it is still trusted."


class ServiceTimeout(AnywhereGpsError):
    code, http_status = "service_timeout", 504
    hint = "The developer service stopped responding. Replug the cable and retry."


class TunnelFailed(AnywhereGpsError):
    code, http_status = "tunnel_failed", 502
    hint = "Could not establish the iOS 17+ developer tunnel. Unlock the iPhone and retry."


class SessionBusy(AnywhereGpsError):
    code, http_status = "session_busy", 409
    hint = "Another operation is already running for this device. Wait for it to finish."


class RateLimited(AnywhereGpsError):
    code, http_status = "rate_limited", 429
    hint = "Wait a moment before searching again."


class GeocodeFailed(AnywhereGpsError):
    code, http_status = "geocode_failed", 502
    hint = "Search is unavailable; click the map or enter coordinates instead."
