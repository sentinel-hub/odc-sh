# ODC-Sentinel Hub

## Getting started

install the ODC datacube core library https://github.com/opendatacube/datacube-core. 

`odc-sh` needs to be installed in the Notebook to run. Use pip install:

```pip install git+https://github.com/sentinel-hub/odc-sh.git```

Set the sentinel hub credential available here https://apps.sentinel-hub.com/dashboard/.

Try to run the test examples. To proiduce the datacube call 

```
resolution = 20  # in meters
longitude = (11.987527, 12.004914)
latitude = (41.990797, 42.018348)

time = ("2019-01-01", "2019-01-04")

ds = dc.load(
    product=DataCollection.SENTINEL2_L1C,
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
)

```

The code will produce a xArray datacube with the following dimensions ["time", "lon", "lat", "bands"]. If only one band is selected under the  measurements, the bands dimension will be ommited. Thus the produced datacube will have dimensions ["time", "lon", "lat"]. You can ommit the measurements information in which case alll the bands will be loaded. 

## Parameters: 

To define the product id and available bands check the following configurations https://docs.sentinel-hub.com/api/latest/data/ or in the DataCollection class of the sentinelhub-py https://github.com/sentinel-hub/sentinelhub-py/blob/master/sentinelhub/data_collections.py.

