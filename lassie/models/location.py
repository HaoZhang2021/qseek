from __future__ import annotations

import math
from functools import cached_property

from pydantic import BaseModel
from pyrocko import orthodrome as od


class Location(BaseModel):
    lat: float
    lon: float
    east_shift: float = 0.0
    north_shift: float = 0.0
    elevation: float = 0.0
    depth: float = 0.0

    class Config:
        keep_untouched = (cached_property,)

    @cached_property
    def effective_lat_lon(self) -> tuple[float, float]:
        """Shift-corrected lat/lon pair of the location."""
        if self.north_shift == 0.0 and self.east_shift == 0.0:
            return self.lat, self.lon
        else:
            return od.ne_to_latlon(
                self.lat, self.lon, self.north_shift, self.east_shift
            )

    def _same_origin(self, other: Location) -> bool:
        return bool(self.lat == other.lat and self.lon == other.lon)

    def surface_distance_to(self, other: Location) -> float:
        """Compute surface distance [m] to other location object."""

        if self._same_origin(other):
            return math.sqrt(
                (self.north_shift - other.north_shift) ** 2
                + (self.east_shift - other.east_shift) ** 2
            )
        return float(
            od.distance_accurate50m_numpy(
                *self.effective_lat_lon, *other.effective_lat_lon
            )[0]
        )

    def distance_to(self, other: Location) -> float:
        if self._same_origin(other):
            return math.sqrt(
                (self.north_shift - other.north_shift) ** 2
                + (self.east_shift - other.east_shift) ** 2
                + ((self.depth + self.elevation) - (other.depth + other.elevation) ** 2)
            )

        else:
            sx, sy, sz = od.geodetic_to_ecef(
                *self.effective_lat_lon, self.elevation - self.depth
            )
            rx, ry, rz = od.geodetic_to_ecef(
                *other.effective_lat_lon, other.elevation - other.depth
            )

            return math.sqrt((sx - rx) ** 2 + (sy - ry) ** 2 + (sz - rz) ** 2)

    def __hash__(self) -> int:
        return hash(
            (
                self.lat,
                self.lon,
                self.east_shift,
                self.north_shift,
                self.elevation,
                self.depth,
            )
        )  # Model has to be hashable.
