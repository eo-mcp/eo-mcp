"""Pydantic schemas and models for eo-mcp."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """WGS84 Bounding Box: [min_lon, min_lat, max_lon, max_lat]."""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @classmethod
    def from_list(cls, coords: List[float]) -> "BoundingBox":
        if len(coords) != 4:
            raise ValueError("Bounding box list must contain 4 coordinates: [min_lon, min_lat, max_lon, max_lat]")
        return cls(min_lon=coords[0], min_lat=coords[1], max_lon=coords[2], max_lat=coords[3])

    def to_list(self) -> List[float]:
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]


class STACSearchResultItem(BaseModel):
    """Normalized STAC Item summary for AI agent context."""
    id: str
    collection: str
    datetime: str
    cloud_cover: Optional[float] = None
    bbox: List[float]
    assets: List[str]
    thumbnail_url: Optional[str] = None


class SpectralIndexResult(BaseModel):
    """Result of an on-the-fly spectral index computation."""
    index: str
    collection: str
    scene_id: str
    datetime: str
    bbox: List[float]
    mean: float
    min: float
    max: float
    std: float
    pixel_count: int
    data_shape: List[int]
    preview_path: Optional[str] = None
    geotiff_path: Optional[str] = None
    histogram: Optional[Dict[str, int]] = None


class ElevationResult(BaseModel):
    """Result of digital elevation queries from Copernicus DEM."""
    bbox: List[float]
    min_elevation_m: float
    max_elevation_m: float
    mean_elevation_m: float
    mean_slope_degrees: Optional[float] = None
    max_slope_degrees: Optional[float] = None
    preview_path: Optional[str] = None
