from tabulate import tabulate
from sentinelhub.download.models import DownloadRequest
from sentinelhub.api.base import SentinelHubService
from typing import Any, Union
from sentinelhub.types import (JsonDict, Json)
from sentinelhub.constants import RequestType
import geopandas as gpd
from shapely.geometry import Polygon

from .commercial_data_base import CommercialSearchResponse, ThumbnailType, \
    AirbusConstellation, Providers, ScopeType, ScopeBundle, SkySatBundle, SkySatType, WorldViewKernel


class SearchResponse:

    def __init__(self, data, **kwargs):
        self.data = data
        self.search_props = []

        for k in kwargs:
            setattr(self, k, kwargs[k])

    def get_ids(self):
        item_ids = []
        if self.typ == SkySatType or self.typ == ScopeType:
            item_ids = [feature["id"] for feature in self.data.features]
        elif self.typ == AirbusConstellation:
            item_ids = [feature["properties"]["id"] for feature in self.data.features]
        elif self.typ == WorldViewKernel:
            item_ids = [feature["catalogId"] for feature in self.data.features]
        else:
            item_ids = [o["id"] for o in self.data]
        return item_ids
    
    def print_coverage(self):
        item_ids = []
        if self.typ == SkySatType or self.typ == ScopeType:
            item_ids = [feature["id"] for feature in self.data.features]
        elif self.typ == AirbusConstellation:
            item_ids = [feature["properties"]["id"] for feature in self.data.features]
        elif self.typ == WorldViewKernel:
            item_ids = [feature["catalogId"] for feature in self.data.features]
        else:
            item_ids = [o["id"] for o in self.data]
        return item_ids

    def print_info(self, **kwargs):
        if hasattr(self,"err"):
            print(self.err)
            return

        if kwargs.get("props"):
            self.search_props = kwargs.get("props")
        
        props = self.search_props
        intersects_perc = []
        if kwargs.get("aoi") and len(self.data.features) > 0:
            data = gpd.GeoDataFrame.from_features(self.data.features)
            aoi_polygon = Polygon(kwargs.get("aoi"))
            aoi_area = aoi_polygon.area

            intersects = [geom.intersection(aoi_polygon) for geom in data.geometry]
            intersects_perc = [intersect.area / aoi_area * 100 for intersect in intersects]   
            props.append("aoi_coverage [%]")
            
        print_data = []
        if self.typ == SkySatType or self.typ == ScopeType:
            print_data = [self.print_fun(feature["properties"], [idx, feature["id"]], [intersects_perc[idx] if len(intersects_perc) > 0 else 0]) for idx, feature in enumerate(self.data.features)]
            self.search_props[0:0] = ["idx", "id"]
        elif self.typ == AirbusConstellation or self.typ == WorldViewKernel:
            print_data = [self.print_fun(feature["properties"], [idx], [intersects_perc[idx] if len(intersects_perc) > 0 else 0]) for idx, feature in enumerate(self.data.features)]
            self.search_props[0:0] = ["idx"]
        elif self.typ == "Normal":
            print_data = [self.print_fun(feature, [idx], [intersects_perc[idx] if len(intersects_perc) > 0 else 0]) for idx, feature in enumerate(self.data)]
            self.search_props[0:0] = ["idx"]
        else:
            print_data = [self.print_fun(self.data, [])]
            
        if print_data:
            print(tabulate(print_data, headers=props))
        else:
            print("No data found.")
        
            
    def print_fun(self, ft, idx, aoi_coverage):
        return idx + [*list(map(lambda h: ft.get(h), self.search_props))] + aoi_coverage


class BaseCommercialClient(SentinelHubService):

    def _call_job(self, endpoint_name: str, payload: dict) -> Json:
        """Makes a POST request to the service"""
        job_url = f"{self.service_url}/{endpoint_name}"
        return self.client.get_json_dict(url=job_url, post_values=payload, request_type=RequestType.POST,
                                         use_session=True)

    def get_bounds(self, bounds: Any):
        btype = "geometry" if type(bounds) is dict else "bbox"
        return dict(zip([btype], [bounds]))

    def search(self, payload) -> CommercialSearchResponse:
        response_info: CommercialSearchResponse = CommercialSearchResponse.from_dict(self._call_job("search", payload))
        return response_info

    def native_search(self, payload) -> CommercialSearchResponse:
        response_info: CommercialSearchResponse = CommercialSearchResponse.from_dict(self._call_job("nativesearch", payload))
        return response_info

    def get_thumb_type(self, typ):
        return ThumbnailType[typ].value


class SentinelHubCommercialData(BaseCommercialClient):

    @staticmethod
    def _get_service_url(base_url: str) -> str:
        """Provides URL to Catalog API"""
        return f"{base_url}/api/v1/dataimport"

    def quotas(self, *args):
        res = self.client.get_json_dict(url=self.service_url+"/quotas" + self.check_arg(args), use_session=True)

        search_props = ["collectionId", "quotaSqkm", "quotaUsed" ]
        return SearchResponse(res["data"], typ="Normal", search_props=search_props)

    def search_airbus(self, typ: AirbusConstellation, bounds: dict, time_from: str, time_to: str, **kwargs: Any):
        kwargs = dict(kwargs, timeRange={"from": time_from, "to": time_to})
        payload = dict(provider=Providers.AIRBUS.value, bounds=self.get_bounds(bounds), data=[{"constellation": typ.value}])
        payload["data"][0]["dataFilter"] = dict()

        for name, val in kwargs.items():
            payload["data"][0]["dataFilter"][name] = val

        search_props = ["id", "acquisitionDate", "resolution", "cloudCover", "incidenceAngle"]
        return SearchResponse(self.search(payload), query=payload, thumb=self.get_thumb_type(typ.value), typ=type(typ),
                              search_props=search_props)

    def search_worldview(self, kernel: WorldViewKernel, bounds: dict, time_from: str, time_to: str, **kwargs: Any):
        kwargs = dict(kwargs, timeRange={"from": time_from, "to": time_to})
        payload = dict(provider=Providers.WORLDVIEW.value, bounds=self.get_bounds(bounds), data=[{"productBands": "4BB",
                                                                                           "productKernel": kernel.value}])
        payload["data"][0]["dataFilter"] = dict()
        for name, val in kwargs.items():
            payload["data"][0]["dataFilter"][name] = val

        search_props = ["catalogId", "sensor", "maxSunAzimuth", "acquisitionDateStart", "meanSunElevation"]
        return SearchResponse(self.search(payload), query=payload, thumb=self.get_thumb_type("WORLDVIEW"),
                              typ=type(kernel), search_props=search_props)

    def search_planet(self, typ: Union[SkySatType, ScopeType], bundle: Union[ScopeBundle, SkySatBundle], bounds: dict, time_from: str,
                      time_to: str, **kwargs: Any):
        planet_api_key = kwargs.get("planestApiKey") if kwargs.get("planetApiKey") else ""
        kwargs = dict(kwargs, timeRange={"from": time_from, "to": time_to})
        payload = dict(provider=Providers.PLANET.value, bounds=self.get_bounds(bounds),
                       data=[{"itemType": typ.value, "productBundle": bundle.value}])
        payload["data"][0]["dataFilter"] = dict()

        if planet_api_key:
            kwargs.pop("planetApiKey")
            payload["planetApiKey"] = planet_api_key

        for name, val in kwargs.items():
            payload["data"][0]["dataFilter"][name] = val

        enm = "SKYSAT" if type(typ) == SkySatType else "SCOPE"
        search_props = ["cloud_cover", "snow_ice_percent", "acquired", "pixel_resolution"]
        return SearchResponse(self.search(payload), query=payload, thumb=self.get_thumb_type(enm), typ=type(typ),
                              search_props=search_props)

    def thumbnail(self, provider_type: ThumbnailType, item_id):
        download_request = DownloadRequest(url=self.service_url + f"/collections/{provider_type}/products/{item_id}/thumbnail",
                                                  request_type=RequestType.GET, use_session=True)
        return self.client.download(download_requests=download_request, decode_data=False)

    def order(self, name: str, query: dict, **kwargs):
        provider = query["provider"]
        if provider == Providers.PLANET.value:
            query['data'][0]["harmonizeTo"] = "NONE"

        # Add selected item_ids
        item_ids = kwargs.get("item_ids")
        if item_ids:
            del query["data"][0]["dataFilter"]
            if provider == Providers.AIRBUS.value:
                query["data"][0]["products"] = []
                for itm_id in item_ids:
                    query["data"][0]["products"].append({"id": itm_id})

            elif provider == Providers.PLANET.value:
                query["data"][0]["itemIds"] = item_ids

            elif provider == Providers.WORLDVIEW.value:
                query["data"][0]["selectedImages"] = item_ids

        payload = dict(name=name, input=query)

        # Set collection id
        col_id = kwargs.get("collectionId")
        if col_id:
            payload["collectionId"] = col_id

        search_props = ["id", "created", "name", "provider", "sqkm", "status"]
        try:
            return SearchResponse(self._call_job("orders", payload), typ="Single", search_props=search_props )
        except:
            return SearchResponse("", err="Error creating order. Check if collection name already exists.")

    def get_orders(self, *args):
        response_info = self.client.get_json_dict(url=self.service_url + "/orders" + self.check_arg(args),
                                                  request_type=RequestType.GET, use_session=True)

        response_info = dict(data=[response_info]) if not response_info.get("data") else response_info
        search_props = ["id", "created", "name", "provider", "sqkm", "status"]
        return SearchResponse(response_info.get("data"), typ="Normal", search_props=search_props)

    def delete_order(self, id_order):
        try:
            self.client.get_json(url=self.service_url + "/orders/" + id_order,
                                 request_type=RequestType.DELETE, use_session=True)
            return SearchResponse("", err=f"Order deleted. {id_order}")
        except ValueError:
            return SearchResponse("", err="Order not found!")

    def confirm_order(self, id_order):
        try:
            data = self.client.get_json(url=self.service_url + "/orders/" + id_order + "/confirm",
                                 request_type=RequestType.POST, use_session=True)
            search_props = ["id", "created", "name", "provider", "sqkm", "status"]
            return SearchResponse(data, typ="Single", search_props=search_props)
        except:
            return SearchResponse("", err="Order not found!")

    def get_collection(self, payload) -> JsonDict:
        payload = dict(input=payload)
        response_info = self._call_job("orders/searchcompatiblecollections", payload)
        search_props = ["id", "name", "created"]

        if response_info.get("data"):
            return SearchResponse(response_info.get("data"), typ="Normal", search_props=search_props)
        else:
            return SearchResponse("", err="No collections found")

    def check_arg(self, args):
        id = ""
        for ar in args:
            id = "/" + ar
            break

        return id
