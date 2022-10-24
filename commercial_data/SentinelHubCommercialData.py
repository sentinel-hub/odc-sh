from sentinelhub.api.base import SentinelHubService
from typing import List, Optional, TypeVar, Generic, Type
from sentinelhub.type_utils import (JsonDict, Json)
from sentinelhub.constants import RequestType
from sentinelhub.api.batch.base import RequestSpec

from CommercialDataBase import CommercialSearchResponse, T, BaseAirbusResponse
from enum import Enum


class Providers(Enum):
    AIRBUS = "AIRBUS"
    PLANET = "PLANET"
    MAXAR = "MAXAR"


class BaseCommercialClient(SentinelHubService):
    def _call_job(self, endpoint_name: str, payload: dict) -> Json:
        """Makes a POST request to the service"""
        print(self)
        print(self.service_url)
        job_url = f"{self.service_url}/{endpoint_name}"
        return self.client.get_json_dict(url=job_url, post_values=payload, request_type=RequestType.POST, use_session=True)


class SentinelHubCommercialData(BaseCommercialClient):

    @staticmethod
    def _get_service_url(base_url: str) -> str:
        """Provides URL to Catalog API"""
        return f"{base_url}/api/v1/dataimport"

    def quotas(self, *args):
        return self.client.get_json_dict(url=self.url+"quotas" + self.check_arg(args), use_session=True)

    def search(self, payload, **kwargs) -> CommercialSearchResponse:
        response_info: CommercialSearchResponse = CommercialSearchResponse.from_dict(self._call_job("search", payload))
        return response_info

    def create_order(self, payload):
        return self._call_job("orders", payload)

    def get_orders(self, *args):
        response_info = self.client.get_json_dict(url=self.url + "orders" + self.check_arg(args),
                                                  request_type=RequestType.GET, use_session=True)
        return response_info

    def delete_order(self, id_order):
        response_info = self.client.get_json(url=self.url + "orders/" + id_order,
                                             request_type=RequestType.DELETE, use_session=True)
        return response_info

    def confirm_order(self, id_order):
        response_info = self.client.get_json(url=self.url + "orders/" + id_order + "/confirm",
                                             request_type=RequestType.POST, use_session=True)
        return response_info

    def get_collection(self, payload) -> JsonDict:
        response_info = self._call_job("orders/searchcompatiblecollections", payload)
        return response_info

    def check_arg(self, args):
        id = ""
        for ar in args:
            id_order = "/" + ar
            break
        return id


