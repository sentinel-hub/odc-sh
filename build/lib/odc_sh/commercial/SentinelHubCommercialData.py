from sentinelhub.api.base import SentinelHubService
from typing import List, Optional, TypeVar, Generic, Type, Any, Union
from sentinelhub.type_utils import (JsonDict, Json)
from sentinelhub.constants import RequestType
from sentinelhub.api.batch.base import RequestSpec

from .CommercialDataBase import CommercialSearchResponse, T, BaseAirbusResponse, ThumbnailType, \
    AirbusConstellation, Providers, ScopeType, ScopeBundle, SkySatBundle, SkySatType, WorldViewKernel


class BaseCommercialClient(SentinelHubService):

    def _call_job(self, endpoint_name: str, payload: dict) -> Json:
        """Makes a POST request to the service"""
        job_url = f"{self.service_url}/{endpoint_name}"
        return self.client.get_json_dict(url=job_url, post_values=payload, request_type=RequestType.POST,
                                         use_session=True)

    def get_bounds(self, bounds: Any):
        btype = "geometry" if type(dict) is list else "bbox"
        return dict(zip([btype], [bounds]))

    def search(self, payload) -> CommercialSearchResponse:
        response_info: CommercialSearchResponse = CommercialSearchResponse.from_dict(self._call_job("search", payload))
        return response_info

    def native_search(self, payload) -> CommercialSearchResponse:
        response_info: CommercialSearchResponse = CommercialSearchResponse.from_dict(self._call_job("nativesearch", payload))
        return response_info


class SentinelHubCommercialData(BaseCommercialClient):

    def quotas(self, *args, **kwargs):
        res = self.client.get_json_dict(url=self.service_url+"/quotas" + self.check_arg(args), use_session=True)
        if kwargs.get("raw"):
            return res
        else:
            s = ""
            for quota in res["data"]:
                s += f"{quota['collectionId']}\nQuota: {quota['quotaSqkm']}\nUsed: {quota['quotaUsed']}\n----------\n"
            return s

    @staticmethod
    def _get_service_url(base_url: str) -> str:
        """Provides URL to Catalog API"""
        return f"{base_url}/api/v1/dataimport"

    def search_airbus(self, typ: AirbusConstellation, bounds: dict, time_from: str, time_to: str, **kwargs: Any):
        kwargs = dict(kwargs, timeRange={"from": time_from, "to": time_to})
        payload = dict(provider=Providers.AIRBUS.value, bounds=self.get_bounds(bounds), data=[{"constellation": typ.value}])
        payload["data"][0]["dataFilter"] = dict()

        for name, val in kwargs.items():
            payload["data"][0]["dataFilter"][name] = val

        return self.search(payload), payload

    def search_worldview(self, kernel: WorldViewKernel, bounds: dict, time_from: str, time_to: str, **kwargs: Any):
        kwargs = dict(kwargs, timeRange={"from": time_from, "to": time_to})
        payload = dict(provider=Providers.WORLDVIEW.value, bounds=self.get_bounds(bounds), data=[{"productBands": "4BB",
                                                                                           "productKernel": kernel.value}])
        payload["data"][0]["dataFilter"] = dict()
        for name, val in kwargs.items():
            payload["data"][0]["dataFilter"][name] = val

        return self.search(payload), payload

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

        return self.search(payload), payload

    def thumbnail(self, provider_type: ThumbnailType, item_id):
        response_info = self.client.get_json_dict(url=self.url + f"collections/{provider_type}/products/{item_id}/thumbnail",
                                                  request_type=RequestType.GET, use_session=True)
        return response_info

    def order(self, name: str, collection_id: str, query: dict, **kwargs):
        provider = query["provider"]
        if provider == Providers.PLANET.value:
            query['data'][0]["harmonizeTo"] = "NONE"

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

        payload = dict(name=name, collectionId=collection_id, input=query)
        return self._call_job("orders", payload)

    def get_orders(self, *args):
        response_info = self.client.get_json_dict(url=self.service_url + "/orders" + self.check_arg(args),
                                                  request_type=RequestType.GET, use_session=True)
        return response_info

    def delete_order(self, id_order):
        response_info = self.client.get_json(url=self.service_url + "/orders/" + id_order,
                                             request_type=RequestType.DELETE, use_session=True)
        return response_info

    def confirm_order(self, id_order):
        response_info = self.client.get_json(url=self.service_url + "/orders/" + id_order + "/confirm",
                                             request_type=RequestType.POST, use_session=True)
        return response_info

    def get_collection(self, payload):
        response_info = self._call_job("orders/searchcompatiblecollections", payload)
        return response_info

    def check_arg(self, args):
        id = ""
        for ar in args:
            id = "/" + ar
            break

        return id


