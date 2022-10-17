import math
import os
import uuid
import warnings

import datacube
import pandas
import numpy as np
import xarray as xr
from datacube.api.query import Query
from datacube.index.hl import prep_eo3
from sentinelhub import (CRS, BBox, BBoxSplitter, SentinelHubCatalog,
                         SentinelHubDownloadClient, SHConfig, SentinelHubBYOC,
                         bbox_to_dimensions, DataCollection)

from sentinelhub.data_collections import DataCollectionDefinition, ServiceUrl
from sentinelhub.data_collections_bands import Band, Unit

from .utils import (build_sentinel_hub_request, features_to_dates,
                    get_catalog_results, get_evalscript, getCollection)

class Singleton(type):
    """A Singleton metaclass."""

    __instance = None

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instance


class Datacube(datacube.Datacube, metaclass=Singleton):
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

    def load_data(self, sources, *args, **kwargs):
        # load other odc sources nornally
        if not self.is_sh_source(sources):
            return super().load_data(sources, *args, **kwargs)
        else:
            return self.process_sh_sources(sources, *args, **kwargs)    
    
    def process_sh_sources(self, sources, *args, **kwargs):
        print("LOADING SENTINEL HUB DATA")
        x1 = x2 = y1 = y2 = None

        product_id = None
        band_names = None

        data = []
        dates = []
        
        for datasets in sources.values:
            for dataset in datasets:
                extent = dataset.metadata_doc["extent"]

                x1 = extent["lon"]["begin"]
                x2 = extent["lon"]["end"]
                y1 = extent["lat"]["begin"]
                y2 = extent["lat"]["end"]

                print("---------------------------------------------")
                sh_resolution = dataset.metadata_doc["properties"]["sh_resolution"]
                time = dataset.metadata_doc["properties"]["datetime"]
                bands = list(dataset.metadata_doc["measurements"].values())

                band_names = [m.name for m in bands]
                band_units = [m.units for m in bands]
                band_sample_types = [m.dtype for m in bands]

                collection = dataset.metadata_doc["properties"]["sh_collection"]
                
                print(
                    f"longitude: {x1}, {x2} \
                    - latitude: {y1}, {y2} \
                    - resolution: {sh_resolution} m \
                    - time: {time.date()} "
                )

                time_slice = self.load_sentinel_hub_data(
                    collection,
                    time,
                    BBox(bbox=[x1, y1, x2, y2], crs=CRS.WGS84),
                    sh_resolution,
                    band_names,
                    band_units,
                    band_sample_types,
                )
                data.append(time_slice)
                dates.append(np.datetime64(time))

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

        date = np.array(dates)
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
    
    def is_sh_source(self, sources):
        for datasets in sources.values:
            for dataset in datasets:
                if "properties" in dataset.metadata_doc and "sh_collection" in dataset.metadata_doc["properties"]:
                        return True
        return False
        

    def load_sentinel_hub_data(
        self,
        collection,
        time,
        bbox_full,
        resolution,
        band_names,
        band_units,
        band_sample_types,
    ):
        # calculate
        size = bbox_to_dimensions(bbox_full, resolution=resolution)

        max_size = 2000.0  # maximal size of image (could be 2500)
        w = math.ceil(size[0] / max_size)
        h = math.ceil(size[1] / max_size)

        image_width = math.ceil(size[0] / w)
        image_height = math.ceil(size[1] / h)

        splitter = BBoxSplitter([bbox_full.geometry], CRS.WGS84, (w, h))
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
                index_y * image_height : (index_y + 1) * image_height,
                index_x * image_width : (index_x + 1) * image_width,
                ...,
            ] = np.flipud(data)

        if single_time_data.shape[-1] == 1:
            single_time_data = single_time_data.squeeze(axis=-1)

        return single_time_data

    def load(self, datasets=None, **kwargs):
        """
        An overloaded load function from Datacube.

        This load method allows for querying the Sentinel HUB REST API to search for datasets
        instead of using the standard database query of datacube.Datacube.

        :rtype: The queried xarray.Dataset.
        """
        datasets = datasets if datasets else self.find_datasets(**kwargs)
        return super().load(datasets=datasets, **kwargs)

    def find_datasets(
        self,
        limit=None,
        **search_terms,
    ):
        """
         Find datasets matching query.
        :param product: api_id of the product to be downloaded. Check DataCollection from sentinel hub py for details.
        :param latitude: (min, max) latitude
        :param longitude: (min, max)  longitude
        :param time: (min, max)  temporal interval of the desired data
        :param measurements: only defined measurements will be downloaded. If not specified, all the bands will be
                             included in the datacube
        :param sh_resolution: only return datasets that have locations
        :param search_terms: additional search parameters
        :param limit: Default number of day slices to be loaded
        :return: A generated list of datacube.model.Dataset objects.

        :rtype: __generator[:class:`datacube.model.Dataset`]
        """
        
        product = search_terms['product']
        
        if not product:
            raise ValueError("product needs to be defined")
            
        query = Query(**search_terms)
        if isinstance(product, DataCollection):
            # verify SH Client credentials before loadind data
            self.validate_credentials()
            
            #only api id is needed
            collection = product
            
            latitude = search_terms['latitude']
            longitude = search_terms['longitude']
            time = search_terms['time']
            sh_resolution = search_terms['sh_resolution'] 
            
            try:
                user_measurements = search_terms['measurements']
            except:
                user_measurements = None            
            
            if not sh_resolution:
                raise ValueError("sh_resolution (m) is not defined")
                
            if not latitude or not longitude:
                raise Exception("Latitude or longitude is missing.")

            if longitude[0] > longitude[1]:
                longitude = (longitude[1], longitude[0])

            if longitude[0] > longitude[1]:
                longitude = (longitude[1], longitude[0])

            bbox = BBox(
                bbox=[longitude[0], latitude[0], longitude[1], latitude[1]],
                crs=CRS.WGS84,
            )
            
            print("Searching for new products")
            query.product = self.generate_product(
                collection, user_measurements, sh_resolution
            )

            # Generate Datacube dataset documents from SH image data
            search_iter = get_catalog_results(
                SentinelHubCatalog(config=self.config), collection, bbox, time
            )
            image_metadata_list = list(search_iter)
            dates = features_to_dates(image_metadata_list)
            
            if not dates:
                raise ValueError(f"No data available for selected period: {time}")

            for date in dates:
                    dataset_metadata = self.make_img_doc(
                        collection,
                        query.product.measurements,
                        date,
                        sh_resolution,
                        bbox,
                    )
                    ds_meta = prep_eo3(dataset_metadata)
                    dataset = datacube.model.Dataset(query.product, ds_meta, uris="")
                    yield dataset
        else:
            for dataset in super().find_datasets(
                limit=limit, **search_terms
            ):
                yield dataset

    def validate_credentials(self):
        if not self.config.sh_client_id or not self.config.sh_client_secret:
            raise ValueError("To use Sentinel Hub, please provide the credentials sh_client_id and sh_client_secret. " 
                             "Usage: en = engine.Datacube(sh_client_id=<YOUR_SH_CLIENT_ID>, sh_client_secret=<YOUR_SH_ CLIENT_SECRET>)). "
                             "You can also set the credentials in your environment settings." 
                             "Check https://sentinelhub-py.readthedocs.io/en/latest/configure.html for more info.")
                
                
    def make_img_doc(
        self, collection, measurements, date, sh_resolution, bbox
    ):
        transform = bbox.get_transform_vector(sh_resolution, sh_resolution)
        doc = {
            "id": str(uuid.uuid4()),
            "$schema": "https://schemas.opendatacube.org/dataset",
            "product": {"name": collection.name},
            "crs": CRS.WGS84.ogc_string(),
            "properties": {
                "odc:processing_datetime": date,
                "odc:file_format": "tif",
                "datetime": date,
                "sh_resolution": sh_resolution,
                "sh_collection": collection,
            },
            "geometry": bbox.geojson,
            "measurements": measurements,
            "grids": {
                "default": dict(
                    shape=[1, 1],
                    transform=[x for d in [transform, (0, 0, 1)] for x in d],
                )
            },  # greed needs to be set but is not used
            "lineage": {"source_datasets": {}},
        }

        return doc

    def generate_product(
        self, collection, user_measurements, sh_resolution
    ):
        """Generates an ODC product from SH datasource metadata.
        :param product_id: The product ID of the SH collection.
        :param user_measurements: Optional; List of predefined measurements selected by the user (can be None).
        :param sh_resolution: the desired output resolution of the product.
        :rtype: A datacube.model.DatasetType product.
        """
        
        if not collection:
            raise ValueError(
                f"Sentinel collection was not defined"
            )

        self.config.sh_base_url = collection.service_url

        bands = list(self.get_measurements(collection, user_measurements))
        collection_details = SentinelHubCatalog(config=self.config).get_collection(
            collection
        )

        definition = dict(
            name=collection.api_id.replace("-", "_"),
            description=collection_details["description"],
            metadata_type="eo3",
            metadata=dict(
                product=dict(name=collection_details["title"]),
                properties={"eo:platform": "Sentinel HUB"},
                id=collection.api_id,
            ),
            measurements=bands,
            storage=dict(
                crs=CRS.WGS84.ogc_string(),
                resolution=dict(latitude=sh_resolution, longitude=sh_resolution),
            ),
        )
        
        prod_res = self.index.products.from_doc(definition)
        print(f"Product created for {collection.name}")
        return prod_res

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
                print(f"measurement: {measurement}")
                yield datacube.model.Measurement(**measurement)

    
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
        
  