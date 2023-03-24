import os
from odc_sh import engine
from sentinelhub import DataCollection

sh_client_id=""
sh_client_secret=""

if not sh_client_id:
    sh_client_id =  os.environ['SH_CLIENT_ID'] 

if not sh_client_secret:
    sh_client_secret = os.environ['SH_CLIENT_SECRET'] 

dc = engine.Datacube(sh_client_id=sh_client_id, sh_client_secret=sh_client_secret)

resolution = 100  # in meters
longitude = (11.987527, 13.704914)
latitude = (41.590797, 42.218348)

time = ("2019-01-01", "2019-01-04")

print("Available SH products:")
print(dc.list_sh_products())

ds = dc.load(
    product=DataCollection.SENTINEL1_IW,
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
)

ds.to_netcdf("s1_all_bands.nc")
