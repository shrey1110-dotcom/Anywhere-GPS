import asyncio

import pytest
from fastapi.testclient import TestClient

from anywhere_gps.app import create_app
from anywhere_gps.errors import *  # noqa: F401,F403
from anywhere_gps.errors import (DeveloperImageMissing, DeveloperModeDisabled, DeviceNotFound, InvalidCoordinates,
                                 MultipleDevices, NotPaired, SessionBusy, UnsupportedIOSVersion)
from anywhere_gps.mock_backend import make_mock_services
from anywhere_gps.models import SessionState
from anywhere_gps.session_manager import SessionManager, retry_with_backoff


# 1 Device discovery
