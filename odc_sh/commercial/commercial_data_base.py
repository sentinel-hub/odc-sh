import datetime as dt
from abc import ABCMeta
from enum import Enum

from dataclasses_json import CatchAll, LetterCase, Undefined
from dataclasses_json import config as dataclass_config
from dataclasses_json import dataclass_json
from dataclasses import dataclass, field
from sentinelhub.api.utils import datetime_config
from typing import List, Optional, TypeVar, Generic, Type, Union

from sentinelhub.types import JsonDict

Self = TypeVar("Self")


class SkySatBundle(Enum):
    ANALYTIC_UDM2 = "analytic_udm2"
    ANALYTIC_SR_UDM2 = "analytic_sr_udm2"
    PANCHROMATIC = "panchromatic"


class ScopeBundle(Enum):
    ANALYTIC_UDM2 = "analytic_udm2"
    ANALYTIC_SR_UDM2 = "analytic_sr_udm2"
    ANALYTIC_8B_UDM2 = "analytic_8b_udm2"
    ANALYTIC_8B_SR_UDM2 = "analytic_8b_sr_udm2"


class Providers(Enum):
    AIRBUS = "AIRBUS"
    PLANET = "PLANET"
    WORLDVIEW = "MAXAR"


class AirbusConstellation(Enum):
    SPOT = "SPOT"
    PLEIADES = "PHR"


class SkySatType(Enum):
    SkySatScene = "SkySatScene"
    SkySatCollect = "SkySatCollect"


class ScopeType(Enum):
    PSScene = "PSScene"


class ThumbnailType(Enum):
    SPOT = "AIRBUS_SPOT"
    PHR = "AIRBUS_PLEIADES"
    SCOPE = "PLANET_SCOPE"
    SKYSAT = "PLANET_SKYSAT"
    WORLDVIEW = "MAXAR_WORLDVIEW"


class WorldViewKernel(Enum):
    CubicConvolution = "CC"
    NearestNeighbour = "NN"
    MTF = "MTF"


class WorldViewSensor(Enum):
    WV01 = "WV01"
    WV02 = "WV02"
    WV03 = "WV03"
    WV04 = "WV04"
    GE01 = "GE01"


class CommercialResponse(metaclass=ABCMeta):
    @classmethod
    def from_dict(cls: Type[Self], json_dict: JsonDict) -> Self:
        """Transforms itself into a dictionary form."""
        raise NotImplementedError("Method should be implemented or provided via `dataclass_json` decorator.")


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class AirbusResponseProperties:
    acquisition_date: Optional[dt.datetime] = field(metadata=datetime_config, default=None)
    acquisition_identifier: Optional[str] = None
    acquisition_station: Optional[str] = None
    activity_id: Optional[str] = None
    archiving_center: Optional[str] = None
    azimuthAngle: float = None
    cloudCover: int = None
    constellation: Optional[str] = None
    correlation_id: Optional[str] = None
    expiration_date: Optional[dt.datetime] = field(metadata=datetime_config, default=None)
    format: Optional[str] = None
    geometry_centroid: Optional[List[float]] = None
    id: str = field(metadata=dataclass_config(field_name="id"), default=None)
    illumination_azimuth_angle: float = None
    illumination_elevationAngle: float = None
    incidence_angle: float = None
    incidence_angle_across_track: float = None
    incidence_angle_along_track: float = None
    last_update_date: Optional[dt.datetime] = field(metadata=datetime_config, default=None)
    organisation_name: Optional[str] = None
    parent_identifier: Optional[str] = None
    platform: Optional[str] = None
    processing_center: Optional[str] = None
    processing_date: Optional[dt.datetime] = field(metadata=datetime_config, default=None)
    processing_level: Optional[str] = None
    processor_name: Optional[str] = None
    product_category: Optional[str] = None
    product_type: Optional[str] = None
    production_status: Optional[str] = None
    publication_date: Optional[dt.datetime] = field(metadata=datetime_config, default=None)
    qualified: bool = False
    resolution: int = None
    snow_cover: int = None
    source_identifier: Optional[str] = None
    spectral_range: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_title: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass(repr=False)
class BaseAirbusResponse(CommercialResponse): # noqa

    _links: dict
    geometry: dict
   # properties: Optional[AirbusResponseProperties]
   # rights: dict[dict, dict, dict]
   # type: str


T = TypeVar("T", BaseAirbusResponse, str)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CommercialSearchResponse(Generic[T]):

    features: List[T]

    @classmethod
    def from_dict(cls: Type[Self], json_dict: JsonDict) -> Self:
        """Transforms itself into a dictionary form."""
        raise NotImplementedError("Method should be implemented or provided via `dataclass_json` decorator.")



