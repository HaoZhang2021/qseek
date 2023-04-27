import glob
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, constr, validator
from pyrocko.model import load_stations
from pyrocko.squirrel import Squirrel

from lassie.ifcs.base import IFC
from lassie.models import Receivers
from lassie.octree import Octree
from lassie.tracers import ConstantVelocityTracer, Tracers

NSL_RE = r"^[a-zA-Z0-9]{0,2}\.[a-zA-Z0-9]{0,5}\.[a-zA-Z0-9]{0,3}$"


class Config(BaseModel):
    stations_file: Path = Path("stations.yaml")

    squirrel_environment: Path = Path(".")
    waveform_data: list[Path] = [Path("data/")]

    time_range: tuple[datetime, datetime] = (
        datetime.fromisoformat("2023-04-11T00:00:00Z"),
        datetime.fromisoformat("2023-04-18T00:00:00Z"),
    )

    station_blacklist: list[constr(regex=NSL_RE)] = ["NE.STA.LOC"]
    ifcs: list[IFC] = []
    tracers: Tracers = Tracers(__root__=[ConstantVelocityTracer()])

    octree: Octree = Octree()

    @validator("time_range")
    def _validate_time_range(cls, range):  # noqa: N805
        assert range[0] < range[1]
        return range

    @validator("stations_file")
    def _validate_stations(cls, path: Path) -> Path:  # noqa: N805
        if not path.exists():
            raise FileNotFoundError(f"Cannot find station file {path}")
        try:
            load_stations(str(path))
        except Exception:
            raise TypeError(f"Cannot load stations from {path}")
        return path

    @validator("waveform_data")
    def _validate_data_paths(cls, paths: list[Path]) -> list[Path]:  # noqa: N805
        for path in paths:
            if "**" in str(path):
                continue
            if not path.exists():
                raise FileNotFoundError(f"Cannot find data path {path}")
        return paths

    def get_cache_path(self) -> Path:
        cache = Path("cache")
        if not cache.exists():
            cache.mkdir()
        return cache

    def get_squirrel(self) -> Squirrel:
        squirrel = Squirrel(str(self.squirrel_environment))
        paths = []
        for path in self.waveform_data:
            if "**" in str(path):
                paths.extend(glob.glob(str(path)))
            else:
                paths.append(str(path))
        squirrel.add(paths)
        return squirrel

    def get_receivers(self) -> Receivers:
        stations = load_stations(self.stations_file)
        return Receivers.from_pyrocko_stations(stations)
