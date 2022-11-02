import math
import os
import uuid

import pandas
import numpy as np
import xarray as xr

from sentinelhub import (CRS, BBox, BBoxSplitter, SentinelHubCatalog,
                         SentinelHubDownloadClient, SHConfig, SentinelHubBYOC,
                         bbox_to_dimensions, DataCollection)

from sentinelhub.data_collections import DataCollectionDefinition, ServiceUrl
from sentinelhub.data_collections_bands import Band, Unit

from .utils import (build_sentinel_hub_request, features_to_dates,
                    get_catalog_results, get_evalscript, getCollection)


class SentinelHubLoader():
    """Extended Datacube object for use with Sentinel Hub.
    Attributes:
    """

    def __init__(self, *args, **kwargs):
        self.config = SHConfig()
        
        #initialize Sentinel hub config with provided credentials or obtain them from env settings
        self.config.sh_client_id = kwargs["sh_client_id"] if "sh_client_id" in kwargs else os.environ.get("SH_CLIENT_ID")
        self.config.sh_client_secret = kwargs["sh_client_secret"] if "sh_client_secret" in kwargs else os.environ.get("SH_CLIENT_SECRET")   

        if "sh_client_id" in kwargs:
            del kwargs["sh_client_id"] 
        
        if "sh_client_secret" in kwargs:
            del kwargs["sh_client_secret"]
        
        super().__init__(*args, **kwargs)

    def process_sh_sources(self, collection, bbox, measurements, sh_resolution, dates, crs):
        print("LOADING SENTINEL HUB DATA")

        x1 = bbox.min_x
        x2 = bbox.max_x
        y1 = bbox.min_y
        y2 = bbox.max_y

        product_id = None
        band_names = None

        data = []
        res_dates = []
        for time in dates:
            print("---------------------------------------------")
            band_names = [m['name'] for m in measurements]
            band_units = [m['units'] for m in measurements]
            band_sample_types = [m['dtype'] for m in measurements]

            print(
                f"longitude: {x1}, {x2}; latitude: {y1}, {y2}; resolution: {sh_resolution} m; crs: {crs}; time: {time.date()} "
            )

            time_slice = self.load_sentinel_hub_data(
                collection,
                time,
                bbox,
                sh_resolution,
                band_names,
                band_units,
                band_sample_types,
                crs
            )
            data.append(time_slice)
            res_dates.append(np.datetime64(time))

        # should not happen
        if not x1 or not x2 or not y1 or not y2:
            raise ValueError("Extent coordinates are not ok")

        # should not happen
        if not band_names or len(band_names) == 0:
            raise ValueError("Bands are not defined")

        x_res = (x2 - x1) / time_slice.shape[0]
        y_res = (y2 - y1) / time_slice.shape[1]

        x_array = np.linspace(
            x1 + x_res / 2, x2 - x_res / 2, time_slice.shape[1], dtype=np.float32
        )

        y_array = np.linspace(
            y1 + y_res / 2, y2 - y_res / 2, time_slice.shape[0], dtype=np.float32
        )

        date = np.array(res_dates)
        img = np.array(data)

        # data are stored as time / latitude (height) / longitude (width)
        dims = ["time", "lat", "lon"]
        coords = dict(time=("time", date), lon=("lon", x_array), lat=("lat", y_array))
        if len(band_names) > 1:
            dims.append("bands")
            coords["bands"] = np.array(band_names)

        return xr.DataArray(
            data=img,
            dims=dims,
            coords=coords,
            attrs=dict(
                description=f"Sentinel HUB export: {product_id}",
                bands=np.array(band_names),
            ),
        )

    def load_sentinel_hub_data(
        self,
        collection,
        time,
        bbox_full,
        resolution,
        band_names,
        band_units,
        band_sample_types,
        crs=CRS.WGS84
    ):

        # calculate
        size = bbox_to_dimensions(bbox_full, resolution=resolution)

        max_size = 2000.0  # maximal size of image (could be 2500)
        w = math.ceil(size[0] / max_size)
        h = math.ceil(size[1] / max_size)

        image_width = math.ceil(size[0] / w)
        image_height = math.ceil(size[1] / h)

        splitter = BBoxSplitter([bbox_full.geometry()], crs, (w, h))
        info_list = splitter.get_info_list()

        # create a list of requests
        list_of_requests = []
        # load data in smaller bbox-es
        for bbox in splitter.get_bbox_list():
            [evalscript, responses] = get_evalscript(
                band_names, band_units, band_sample_types
            )

            list_of_requests.append(
                build_sentinel_hub_request(
                    self.config,
                    collection,
                    time.date(),
                    (image_width, image_height),
                    bbox,
                    evalscript,
                    responses,
                )
            )

        list_of_requests = [request.download_list[0] for request in list_of_requests]

        # download data with multiple threads
        resp_data = SentinelHubDownloadClient(config=self.config).download(
            list_of_requests, show_progress=True, max_threads=20
        )

        # prepare data storage
        single_time_data = np.zeros(
            (image_height * h, image_width * w, len(band_names)), dtype=np.float32
        )

        # load and copy data - as the multi-band response is different, we need to parse the response differently
        for data, info in zip(resp_data, info_list):
            if len(band_names) > 1:
                data = np.stack([data[f"{band}.tif"] for band in band_names], axis=-1)

            index_x = int(info["index_x"])
            index_y = int(info["index_y"])

            single_time_data[
            index_y * image_height: (index_y + 1) * image_height,
            index_x * image_width: (index_x + 1) * image_width,
            ...,
            ] = np.flipud(data)

        if single_time_data.shape[-1] == 1:
            single_time_data = single_time_data.squeeze(axis=-1)

        return single_time_data

    def load(self, product, latitude, longitude, time, **kwargs):
        """
        Simulates the load function from Datacube without actually needing the ODC environment.

        This load method allows for querying the Sentinel HUB REST API to search for datasets
        instead of using the standard database query of datacube.Datacube.

        :rtype: The queried xarray.Dataset.
        """

        if not product:
            raise ValueError("product needs to be defined")

        if isinstance(product, DataCollection):
            # verify SH Client credentials before loadind data
            self.validate_credentials()

            # only api id is needed
            collection = product

            self.config.sh_base_url = collection.service_url

            # load initial parameters
            crs = CRS.ogc_string(kwargs['crs']) if 'crs' in kwargs.keys() else CRS.WGS84
            user_measurements = kwargs['measurements'] if 'measurements' in kwargs.keys() else None
            sh_resolution = kwargs['sh_resolution'] if 'sh_resolution' in kwargs.keys() else None

            if not sh_resolution:
                raise ValueError("sh_resolution (m) is not defined")

            if not latitude or not longitude:
                raise ValueError("Latitude or longitude is missing.")

            if not time:
                raise ValueError("Time is missing.")

            if longitude[0] > longitude[1]:
                longitude = (longitude[1], longitude[0])

            if longitude[0] > longitude[1]:
                longitude = (longitude[1], longitude[0])

            print(longitude, latitude)

            bbox = BBox(
                bbox=[longitude[0], latitude[0], longitude[1], latitude[1]],
                crs=crs,
            )

            measurements = list(self.get_measurements(collection, user_measurements))

            print(collection)

            search_iter = get_catalog_results(
                SentinelHubCatalog(config=self.config), collection, bbox, time
            )

            image_metadata_list = list(search_iter)
            dates = features_to_dates(image_metadata_list)

            if not dates:
                raise ValueError(f"No data available for selected period: {time}")

            return self.process_sh_sources(collection, bbox, measurements, sh_resolution, dates, crs)
        else:
            raise ValueError("This loader only supports Sentinel HUB products. Use dc = engine.Datacube() for ODC products.")



    def validate_credentials(self):
        if not self.config.sh_client_id or not self.config.sh_client_secret:
            raise ValueError("To use Sentinel Hub, please provide the credentials sh_client_id and sh_client_secret. " 
                             "Usage: en = engine.Datacube(sh_client_id=<YOUR_SH_CLIENT_ID>, "
                             "sh_client_secret=<YOUR_SH_ CLIENT_SECRET>)). "
                             "You can also set the credentials in your environment settings." 
                             "Check https://sentinelhub-py.readthedocs.io/en/latest/configure.html for more info.")

    def get_measurements(self, collection, measurements=None):
        bands = collection.bands

        # verify that all requested measurements match the available collection bands
        if measurements:
            bands_names = {band.name for band in bands}
            for measurement in measurements:
                if measurement not in bands_names:
                    raise ValueError(
                        f"Measurement {measurement} is not available in bands {bands_names}"
                    )

        # only store bands defined by the user measurements
        for band in bands:
            if not measurements or band.name in measurements:
                measurement = dict(
                    name=band.name,
                    units=band.units[0].name,
                    dtype=np.dtype(band.output_types[0]).name,
                    nodata=0,
                )
                yield measurement
    
    def list_sh_products(self):
        cols = ['name',
            'api_id',
            'service_url',
            'sensor_type',
            'collection_type',
            'resolution',
        ]
        rows = [[getattr(pr, col, None) for col in cols] for pr in self.get_available_collections()]
        return pandas.DataFrame(rows, columns=cols).set_index('name', drop=False)
     
    def dataframe_for_band(self, collection_name, bands):
        band_info = pandas.DataFrame(bands)
        prod_name = np.empty(len(band_info), dtype=object)
        prod_name[:] = collection_name
        band_info.insert(0, "product_name", prod_name)
        return band_info   
        
        
    def list_sh_bands(self):
        bands_info = []
        for col in self.get_available_collections():
            if not any(bands_info):
                bands_info = self.dataframe_for_band(col.name, col.bands)
            else:
                bands_info = pandas.concat([bands_info, self.dataframe_for_band(col.name, col.bands)]) 
        return bands_info
    
        
    
    
    def get_available_collections(self):
        return filter(lambda col: col.value.bands, DataCollection.get_available_collections())
    
    
    def get_collection(self, collection_name):
        res = list(filter(lambda col: col.name == collection_name, self.get_available_collections()))
        if(any(res)):
            return res[0]
        else:
            raise ValueError(f'Collection with name: {collection_name} does not exist.')
            
            
    def get_BYOC_collection(self, collection_id):
        byoc = SentinelHubBYOC(self.config)
        my_collection = byoc.get_collection(collection_id)
        
        if not my_collection:
            raise ValueError(f'Collection with id: {collection_id} does not exist.')
        
        collection_bands = my_collection["additionalData"]["bands"]
        bands = tuple(
            Band(band_name, (Unit.DN, ), (np.uint16, )) for band_name in collection_bands
        )
        
        return DataCollection.define_byoc(my_collection["id"], name=my_collection["id"], bands=bands, service_url=ServiceUrl.MAIN)
        
  