"""Unit tests for dynamic credential management and status inspection."""

import os
import json
import pytest
from eo_mcp.config import update_credential, get_credentials_status_summary
from eo_mcp.providers.cdse import get_cdse_token, generate_cdse_download_info
from eo_mcp.server import configure_credentials, get_credential_status, download_copernicus_granule


def test_update_credential_cdse():
    res = update_credential("cdse", username="test_user@isu.edu", password="test_password_123")
    assert res["status"] == "configured"
    assert os.getenv("CDSE_USERNAME") == "test_user@isu.edu"
    assert os.getenv("CDSE_PASSWORD") == "test_password_123"


def test_update_credential_earthdata():
    res = update_credential("earthdata", token="nasa_ed_token_xyz")
    assert res["status"] == "configured"
    assert os.getenv("EARTHDATA_TOKEN") == "nasa_ed_token_xyz"


def test_update_credential_planetary_computer():
    res = update_credential("planetary_computer", api_key="pc_sub_key_123")
    assert res["status"] == "configured"
    assert os.getenv("PC_SDK_SUBSCRIPTION_KEY") == "pc_sub_key_123"


def test_update_credential_firms():
    res = update_credential("firms", api_key="firms_map_key_456")
    assert res["status"] == "configured"
    assert os.getenv("MAP_KEY") == "firms_map_key_456"


def test_get_credentials_status_summary():
    os.environ["CDSE_USERNAME"] = "anwar@isu.edu"
    os.environ["CDSE_PASSWORD"] = "secret123"
    summary = get_credentials_status_summary()

    assert summary["zero_config_public_mode_active"] is True
    assert summary["providers"]["cdse"]["configured"] is True
    assert "an***@isu.edu" in summary["providers"]["cdse"]["identity"]


def test_server_configure_and_status_tools():
    # Test tool wrapper execution
    res_str = configure_credentials(provider="cdse", username="demo@domain.com", password="mypassword")
    res = json.loads(res_str)
    assert res["status"] == "configured"

    status_str = get_credential_status()
    status = json.loads(status_str)
    assert status["providers"]["cdse"]["configured"] is True


def test_generate_cdse_download_info():
    info = generate_cdse_download_info("S2A_MSIL2A_TEST_GRANULE")
    assert "download_endpoint" in info or "download_url" in info
