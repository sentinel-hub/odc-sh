import datetime as dt
from abc import ABCMeta

from dataclasses_json import CatchAll, LetterCase, Undefined
from dataclasses_json import config as dataclass_config
from dataclasses_json import dataclass_json
from dataclasses import dataclass, field
from sentinelhub.api.utils import datetime_config
from typing import List, Optional, TypeVar, Generic, Type

from sentinelhub.type_utils import JsonDict

Self = TypeVar("Self")


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


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass(repr=False)
class BaseAirbusResponse(CommercialResponse): # noqa

    _links: str
    geometry: dict[str, List[List[int]]]
    properties: Optional[AirbusResponseProperties]
    rights: dict[dict, dict, dict]
    type: str


T = TypeVar("T", BaseAirbusResponse, str)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CommercialSearchResponse(Generic[T]):

    features: List[T]

    @classmethod
    def from_dict(cls: Type[Self], json_dict: JsonDict) -> Self:
        """Transforms itself into a dictionary form."""
        raise NotImplementedError("Method should be implemented or provided via `dataclass_json` decorator.")



