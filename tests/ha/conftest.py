"""Use real Home Assistant fixtures, not locally invented API stubs."""

import pytest


@pytest.fixture(autouse=True)
def custom_integrations_enabled(enable_custom_integrations):
    """Allow this custom component to be loaded by the Home Assistant test harness."""
