from sentinelhub import DataCollection

from odc_sh import engine

sh_client_id=""
sh_client_secret=""

dc = engine.Datacube(sh_client_id=sh_client_id, sh_client_secret=sh_client_secret)

p = dc.list_products()

resolution = 300  # in meters
longitude = (12.987527, 13.704914)
latitude = (41.590797, 42.218348)

time = ("2019-01-01", "2019-01-04")

dc.list_products

ds = dc.load(
    product=DataCollection.SENTINEL3_OLCI,
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
)

# print(ds.head)

ds.to_netcdf("s3_all_bands.nc")
