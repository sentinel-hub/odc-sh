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

resolution = 300  # in meters
crs = 'EPSG:4326'
longitude = (12.987527, 13.104914)
latitude = (41.990797, 42.218348)

#crs = 'EPSG:3857'
#longitude = (1385585.909539,1396057.845357)
#latitude = (5141536.685675, 5148568.905287)

time = ("2019-01-01", "2019-01-04")

ds = dc.load(
    product=DataCollection.SENTINEL3_OLCI,
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
    crs=crs
)

print(ds.head)

new = ds.sel(time=ds.time[0], bands=['B04','B03','B02'], drop=True).transpose('bands', 'y', 'x')
new = new.rio.set_crs(ds.rio.crs)
new.rio.to_raster(raster_path="image_cog.tif", driver="COG")

#ds.to_netcdf("s3_all_bands.nc")
