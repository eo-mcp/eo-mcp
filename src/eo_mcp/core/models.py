"""Pydantic schemas and models for eo-mcp."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


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


class CompactSTACItem(BaseModel):
    """High-signal, token-optimized STAC Item summary for AI agent context."""
    id: str = Field(description="Unique scene identifier")
    platform: str = Field(description="Satellite platform or constellation (e.g. sentinel-2b, landsat-8)")
    datetime: str = Field(description="Acquisition datetime (ISO 8601 UTC)")
    cloud_cover: Optional[float] = Field(None, description="Cloud cover percentage (0-100), rounded to 1 decimal place")
    bbox: List[float] = Field(description="[min_lon, min_lat, max_lon, max_lat] in WGS84, rounded to 4 decimals")
    bands: List[str] = Field(description="Normalized core science spectral or sensor band identifiers")

    @field_validator("bbox", mode="before")
    @classmethod
    def round_bbox(cls, v: Any) -> List[float]:
        if isinstance(v, (list, tuple)):
            return [round(float(c), 4) for c in v]
        return v

    @field_validator("cloud_cover", mode="before")
    @classmethod
    def round_cloud_cover(cls, v: Any) -> Optional[float]:
        if v is not None:
            return round(float(v), 1)
        return None


class CompactSTACResponse(BaseModel):
    """Token-budget compliant STAC search response container."""
    count: int = Field(description="Number of scenes returned")
    scenes: List[CompactSTACItem] = Field(description="List of compact scene summaries")
    collection: Optional[str] = Field(None, description="Target STAC collection identifier")


class STACSearchResultItem(BaseModel):
    """Normalized STAC Item summary for AI agent context."""
    id: str
    collection: str
    datetime: str
    cloud_cover: Optional[float] = None
    bbox: List[float]
    assets: List[str]
    thumbnail_url: Optional[str] = None
    platform: Optional[str] = None
    bands: Optional[List[str]] = None


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
