"""Google Earth Engine session initialization and credential handling.

Manages connection to Google Earth Engine via user credentials, service account keys,
or environment variables (GEE_PROJECT, GOOGLE_APPLICATION_CREDENTIALS).
Provides resilient soft-import guards so eo-mcp functions seamlessly even when
earthengine-api is not yet installed or authenticated.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Soft import guard for earthengine-api
try:
    import ee
    _EE_INSTALLED = True
except (ImportError, OSError):
    ee = None
    _EE_INSTALLED = False

_EE_INITIALIZED = False
_ACTIVE_PROJECT: Optional[str] = None


def is_ee_installed() -> bool:
    """Check if the earthengine-api package is installed."""
    return _EE_INSTALLED


def is_ee_initialized() -> bool:
    """Check if Earth Engine has been successfully initialized in this session."""
    return _EE_INITIALIZED


def is_ee_available() -> bool:
    """Check if Earth Engine is installed and initialized."""
    return _EE_INSTALLED and _EE_INITIALIZED


def get_ee_status() -> Dict[str, Any]:
    """Return diagnostic status of Earth Engine integration."""
    return {
        "installed": _EE_INSTALLED,
        "initialized": _EE_INITIALIZED,
        "active_project": _ACTIVE_PROJECT,
        "env_project": os.getenv("GEE_PROJECT"),
        "has_service_account": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
    }


def init_ee(
    project_id: str | None = None,
    service_account_key: str | Path | None = None,
) -> Dict[str, Any]:
    """Initialize the Earth Engine Python API.

    Resolves credentials in the following order:
    1. Direct service_account_key file parameter
    2. Direct project_id parameter
    3. GOOGLE_APPLICATION_CREDENTIALS environment variable
    4. GEE_PROJECT environment variable
    5. Cached credentials from 'earthengine authenticate'

    Args:
        project_id: Optional Google Cloud project ID with Earth Engine enabled.
        service_account_key: Optional path to a GCP service account JSON key file.

    Returns:
        Dictionary reporting initialization status and resolved project.

    Raises:
        ImportError: If earthengine-api is not installed.
        RuntimeError: If authentication or initialization fails.
    """
    global _EE_INITIALIZED, _ACTIVE_PROJECT

    if not _EE_INSTALLED:
        raise ImportError(
            "earthengine-api is not installed. "
            "Install it via: uv pip install 'earthengine-api>=0.1.390' "
            "or pip install 'eo-mcp[gee]'"
        )

    resolved_project = project_id or os.getenv("GEE_PROJECT")
    key_path = service_account_key or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    try:
        if key_path:
            resolved_key_path = Path(key_path)
            if not resolved_key_path.exists():
                raise FileNotFoundError(f"Service account key not found at: {key_path}")

            with open(resolved_key_path, encoding="utf-8") as f:
                key_data = json.load(f)
            client_email = key_data["client_email"]
            credentials = ee.ServiceAccountCredentials(client_email, str(resolved_key_path))
            ee.Initialize(credentials, project=resolved_project)
            logger.info("Earth Engine initialized via service account: %s", client_email)
        else:
            if resolved_project:
                ee.Initialize(project=resolved_project)
            else:
                ee.Initialize()
            logger.info("Earth Engine initialized via user/default credentials.")

        _EE_INITIALIZED = True
        _ACTIVE_PROJECT = resolved_project or "default"
        return {
            "status": "success",
            "message": f"Earth Engine initialized successfully (project: {_ACTIVE_PROJECT}).",
            "project": _ACTIVE_PROJECT,
        }
    except Exception as e:
        _EE_INITIALIZED = False
        _ACTIVE_PROJECT = None
        error_msg = str(e)
        logger.error("Failed to initialize Earth Engine: %s", error_msg)
        raise RuntimeError(
            f"Earth Engine initialization failed: {error_msg}. "
            "Ensure you have authenticated via 'earthengine authenticate' "
            "or supplied a valid project_id/service_account_key."
        ) from e


def require_ee():
    """Ensure Earth Engine is available and return the ee module.

    Raises:
        ImportError: If earthengine-api is not installed.
        RuntimeError: If Earth Engine is not initialized.
    """
    if not _EE_INSTALLED:
        raise ImportError(
            "earthengine-api is not installed. "
            "Install it via: uv pip install 'earthengine-api>=0.1.390' "
            "or pip install 'eo-mcp[gee]'"
        )
    if not _EE_INITIALIZED:
        # Attempt auto-initialization from environment if GEE_PROJECT is set
        env_project = os.getenv("GEE_PROJECT")
        try:
            init_ee(project_id=env_project)
        except Exception as e:
            raise RuntimeError(
                "Earth Engine is not initialized. Call 'gee_init' first with your "
                "Google Cloud project ID (e.g., gee_init(project_id='my-project'))."
            ) from e
    return ee
