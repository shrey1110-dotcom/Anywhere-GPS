import httpx
import pytest
from fastapi.testclient import TestClient

from anywhere_gps import compatibility_report as cr
from anywhere_gps.app import create_app
from anywhere_gps.config import Settings
from anywhere_gps.errors import RateLimited
from anywhere_gps.geocode import Geocoder
from anywhere_gps.location_restore import ProbeReading, verify_restore
from anywhere_gps.mock_backend import make_mock_services


def test_verify_restore_cases():
    tgt = (40.69, -74.04)
    assert not verify_restore(ProbeReading(40.69, -74.04, True, 1), tgt)["verified"]
    assert verify_restore(ProbeReading(37.0, -122.0, False, 1), tgt)["verified"]
    assert verify_restore(ProbeReading(37.0, -122.0, False, 99), tgt)["reason"] == "stale_reading"
    assert verify_restore(ProbeReading(40.69, -74.04, None, 1), tgt)["reason"] == "inconclusive_near_target"
    assert not verify_restore(ProbeReading(37.0, -122.0, None, 1), tgt)["verified"]  # unknown source != proof


def test_restore_verify_endpoint(settings):
    services, farm = make_mock_services()
    farm.add("U1")
    with TestClient(create_app(settings, services)) as c:
        c.post("/api/location", json={"latitude": 1, "longitude": 2})
        c.post("/api/location/clear", json={})
        r = c.post("/api/restore/verify", json={"latitude": 40, "longitude": 3, "is_simulated_by_software": False,
                                                "age_seconds": 2})
        assert r.json()["verified"] is True
        assert c.get("/api/session").json()["last_restore"]["verified"] is True


def test_favorites_roundtrip(settings):
    services, _ = make_mock_services()
    with TestClient(create_app(settings, services)) as c:
        f = c.post("/api/favorites", json={"name": "Home", "latitude": 1.5, "longitude": 2.5}).json()
        assert c.get("/api/favorites").json() == [f]
        assert c.post("/api/favorites", json={"name": "x", "latitude": 99, "longitude": 0}).status_code == 422
        assert c.delete(f"/api/favorites/{f['id']}").json() == {"removed": True}
        assert c.get("/api/favorites").json() == []


async def test_geocoder_rate_limit_and_cache(tmp_path):
    hits = []

    def handler(req: httpx.Request):
        hits.append(req.url.params["q"])
        return httpx.Response(200, json=[{"display_name": "Paris", "lat": "48.85", "lon": "2.35"}])
    s = Settings(home=tmp_path, geocode_min_interval=5)
    g = Geocoder(s, httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={"User-Agent": "t"}))
    assert (await g.search("paris"))[0]["latitude"] == 48.85
    assert await g.search("Paris")      # cache hit, no network
    assert len(hits) == 1
    with pytest.raises(RateLimited):
        await g.search("london")        # 2nd distinct query inside the interval is refused, not queued
    assert len(hits) == 1


def test_compat_report_rejects_unevidenced_claims():
    bad = {"app": "ADP Mobile", "outcome": "approved_test_acceptance_verified", "physical_device": "iPhone 15 / 18.0"}
    assert cr.validate_entry(bad)       # needs authorization_reference
    ok = {"app": "ADP Mobile", "outcome": "gps_permission_behavior_observed", "physical_device": "iPhone 15 / 18.0"}
    rep = cr.build_report([bad, ok])
    adp = next(r for r in rep["rows"] if r["app"] == "ADP Mobile")
    assert adp["outcomes"] == ["gps_permission_behavior_observed"] and len(rep["rejected_entries"]) == 1
    assert all(r["outcomes"] == ["not_tested"] for r in rep["rows"] if r["app"] != "ADP Mobile")
    assert cr.build_report([])["rows"][0]["outcomes"] == ["not_tested"]
