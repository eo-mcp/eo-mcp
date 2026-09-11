"""Cloud-native COG Windowed Streaming Engine.

Leverages GDAL /vsicurl/ and rasterio windowed reads to fetch ONLY the pixels
intersecting the requested bounding box, without downloading full granules.
"""

import math
from typing import Tuple, Optional
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds


def stream_cog_window(
    asset_url: str,
    bbox_wgs84: Tuple[float, float, float, float],
    resampling_factor: float = 1.0
) -> Tuple[np.ndarray, dict]:
    """
    Stream only the pixel window intersecting bbox_wgs84 from a remote Cloud-Optimized GeoTIFF.

    Args:
        asset_url: Remote HTTP/S3 URL to the Cloud Optimized GeoTIFF.
        bbox_wgs84: (min_lon, min_lat, max_lon, max_lat) in EPSG:4326.
        resampling_factor: Optional downsampling factor (e.g. 0.5 for fast preview).

    Returns:
        (data_array, profile_dict)
    """
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84

    # Ensure URL is accessible via GDAL /vsicurl/ if remote HTTP
    if asset_url.startswith("http://") or asset_url.startswith("https://"):
        vsicurl_url = f"/vsicurl/{asset_url}"
    else:
        vsicurl_url = asset_url

    with rasterio.Env(
        AWS_NO_SIGN_REQUEST="YES",
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
        VSI_CACHE="TRUE",
        VSI_CACHE_SIZE="5000000"
    ):
        with rasterio.open(vsicurl_url) as src:
            # Reproject WGS84 bounding box to raster native CRS
            if src.crs and src.crs.to_string() != "EPSG:4326":
                left, bottom, right, top = transform_bounds(
                    "EPSG:4326", src.crs, min_lon, min_lat, max_lon, max_lat
                )
            else:
                left, bottom, right, top = min_lon, min_lat, max_lon, max_lat

            # Determine pixel window
            window = from_bounds(left, bottom, right, top, transform=src.transform)
            
            # Read only the subset
            out_shape = None
            if resampling_factor != 1.0:
                out_shape = (
                    src.count,
                    max(1, int(window.height * resampling_factor)),
                    max(1, int(window.width * resampling_factor))
                )

            data = src.read(window=window, out_shape=out_shape, masked=True)
            
            # Compute new window transform
            win_transform = src.window_transform(window)
            profile = src.profile.copy()
            profile.update({
                "height": data.shape[1],
                "width": data.shape[2],
                "transform": win_transform
            })

            return data, profile
