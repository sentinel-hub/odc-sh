import os
from odc_sh import engine
from sentinelhub import (CRS, DataCollection)

sh_client_id=""
sh_client_secret=""

if not sh_client_id:
    sh_client_id =  os.environ['SH_CLIENT_ID'] 

if not sh_client_secret:
    sh_client_secret = os.environ['SH_CLIENT_SECRET'] 

dc = engine.Datacube(sh_client_id=sh_client_id, sh_client_secret=sh_client_secret)

p = dc.list_products()

resolution = 100  # in meters
longitude = (10.259838, 10.367656)
latitude = (36.476515, 36.546329)
time = ("2019-01-01", "2019-01-04")

# IMPORTANT!!! : due to different resolution of SENTINEL3_SLSTR bands
# https://docs.sentinel-hub.com/api/latest/data/sentinel-3-slstr-l1b/#available-bands-and-data,
# we can only load together bands from {S1-S6} or {S7, S8, S9, F1, F2}. Loading all band together
# will throw a bad request error: "The script can only use bands of the same resolution! ..."

ds = dc.load(
    product=DataCollection.SENTINEL3_SLSTR,
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
    measurements=["S1", "S2", "S3"],
)

print(ds.head)

