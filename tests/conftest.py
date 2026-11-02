import pytest

from anywhere_gps.config import Settings
from anywhere_gps.mock_backend import make_mock_services
from anywhere_gps.session_manager import SessionManager


async def no_sleep(_):
    return None


@pytest.fixture
def farm_services():
    services, farm = make_mock_services()
    farm.add("UDID-A", name="Phone A")
    return services, farm


@pytest.fixture
def mgr(farm_services):
    services, _ = farm_services
    return SessionManager(services, op_timeout=1, connect_attempts=3, backoff_base=0, monitor_interval=0.01,
                          sleep=no_sleep)


@pytest.fixture
def settings(tmp_path):
    return Settings(home=tmp_path, backend="mock")
