"""FastAPI app. Binds to localhost by default; rejects cross-origin browser requests to protect device controls."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import compatibility_report, diagnostics
from .config import Settings
from .errors import AnywhereGpsError, InvalidCoordinates
from .favorites import Favorites
from .geocode import Geocoder
from .location_restore import ProbeReading, verify_restore
from .logging_setup import setup_logging, write_crash_report
from .models import Services, validate_coordinates
from .session_manager import SessionManager

log = logging.getLogger("anywhere_gps.app")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
ROOT = Path(__file__).resolve().parents[2]


class LocationReq(BaseModel):
    udid: str | None = None
    latitude: float
    longitude: float


class UdidReq(BaseModel):
    udid: str | None = None


class FavoriteReq(BaseModel):
    name: str
    latitude: float
    longitude: float


class ProbeReq(BaseModel):
    udid: str | None = None
    latitude: float
    longitude: float
    is_simulated_by_software: bool | None = None
    age_seconds: float


def default_services(settings: Settings) -> tuple[Services, object | None]:
    if settings.backend == "mock":
        from .mock_backend import make_mock_services
        services, farm = make_mock_services()
        farm.add("MOCK-0000-0001", name="Mock iPhone (no real device)")
        return services, farm
    from .developer_setup import RealDeveloperSetup
    from .device_discovery import UsbmuxDiscovery
    from .location_simulator import DvtLocationSimulator
    return Services(UsbmuxDiscovery(), RealDeveloperSetup(settings.op_timeout),
                    DvtLocationSimulator(timeout=settings.op_timeout), kind="real"), None


def create_app(settings: Settings | None = None, services: Services | None = None,
               geocoder: Geocoder | None = None) -> FastAPI:
    settings = settings or Settings()
    setup_logging(settings)
    if services is None:
        services, _ = default_services(settings)
    mgr = SessionManager(services, op_timeout=settings.op_timeout, connect_attempts=settings.connect_attempts,
                         backoff_base=settings.backoff_base, monitor_interval=settings.monitor_interval)
    favorites = Favorites(settings.home)
    geo = geocoder or Geocoder(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("starting", extra={"ctx": {"backend": services.kind}})
        yield
        log.info("shutting down: restoring any simulated locations")
        await mgr.shutdown()

    app = FastAPI(title="Anywhere GPS", lifespan=lifespan)
    app.state.mgr, app.state.settings = mgr, settings

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = urlparse("//" + (request.headers.get("host") or "")).hostname or ""
        origin = request.headers.get("origin")
        if host and host not in LOCAL_HOSTS and host != "testserver":
            return JSONResponse({"code": "forbidden_host", "message": "Only localhost may use this API.",
                                 "hint": ""}, status_code=403)
        if origin and (urlparse(origin).hostname or "") not in {"127.0.0.1", "localhost", "::1"}:
            return JSONResponse({"code": "forbidden_origin", "message": "Cross-origin request blocked.",
                                 "hint": "Open the app at http://127.0.0.1:%d" % settings.port}, status_code=403)
        return await call_next(request)

    @app.exception_handler(AnywhereGpsError)
    async def on_known(_: Request, e: AnywhereGpsError):
        return JSONResponse(e.to_dict(), status_code=e.http_status)

    @app.exception_handler(Exception)
    async def on_crash(_: Request, e: Exception):
        path = write_crash_report(settings, e, "request")
        return JSONResponse({"code": "internal_error", "message": "Unexpected backend error.",
                             "hint": f"A crash report was saved to {path}"}, status_code=500)

    @app.get("/api/health")
    async def health():
        return {"ok": True, "backend": services.kind, "mock": services.kind == "mock"}

    @app.get("/api/devices")
    async def devices():
        return {"backend": services.kind, "devices": [d.to_dict() for d in await services.discovery.list_devices()]}

    @app.get("/api/devices/{udid}/readiness")
    async def readiness(udid: str):
        return (await services.setup.check(udid)).to_dict()

    @app.post("/api/devices/{udid}/developer-image/mount")
    async def mount(udid: str):
        await services.setup.mount_image(udid)
        return (await services.setup.check(udid)).to_dict()

    @app.get("/api/session")
    async def session(udid: str | None = None):
        resolved = await mgr.resolve_udid(udid)
        return mgr.status(resolved)

    @app.post("/api/location")
    async def set_location(req: LocationReq):
        return await mgr.set_location(req.udid, req.latitude, req.longitude)

    @app.post("/api/location/clear")
    async def clear_location(req: UdidReq):
        return await mgr.clear_location(req.udid)

    @app.post("/api/restore/verify")
    async def verify(req: ProbeReq):
        udid = await mgr.resolve_udid(req.udid)
        sess = mgr._session(udid)
        prev = (sess.last_restore or {}).get("previous_target")
        res = verify_restore(ProbeReading(req.latitude, req.longitude, req.is_simulated_by_software, req.age_seconds),
                             (prev["latitude"], prev["longitude"]) if prev else None)
        if sess.last_restore is not None:
            sess.last_restore.update({"verified": res["verified"], "verification": res["reason"],
                                      "message": res["message"]})
        return res

    @app.get("/api/favorites")
    async def list_favs():
        return favorites.list()

    @app.post("/api/favorites")
    async def add_fav(req: FavoriteReq):
        lat, lon = validate_coordinates(req.latitude, req.longitude)
        return favorites.add(req.name, lat, lon)

    @app.delete("/api/favorites/{fid}")
    async def del_fav(fid: str):
        return {"removed": favorites.remove(fid)}

    @app.get("/api/geocode")
    async def geocode(q: str = Query(min_length=1, max_length=200)):
        return await geo.search(q)

    @app.get("/api/diagnostics")
    async def diag():
        return {"host": diagnostics.host_report(), "backend": services.kind, "sessions": mgr.all_status()}

    @app.get("/api/compatibility")
    async def compat():
        return compatibility_report.build_report(compatibility_report.load_results(ROOT / "compat" / "results.json"))

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    return app


def main() -> None:
    import uvicorn
    s = Settings()
    uvicorn.run(create_app(s), host=s.host, port=s.port, log_level="info")


if __name__ == "__main__":
    main()
