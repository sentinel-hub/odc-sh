from sentinelhub import DataCollection

from odc_sh import engine

sh_client_id=""
sh_client_secret=""

dc = engine.Datacube(sh_client_id=sh_client_id, sh_client_secret=sh_client_secret)

p = dc.list_sh_products()

resolution = 100  # in meters
longitude = (11.987527, 12.704914)
latitude = (42.590797, 43.218348)

time = ("2019-01-01", "2019-01-04")

dc.list_products

ds = dc.load(
    product=DataCollection.SENTINEL2_L1C,
    measurements=["B02", "B03", "B04"],
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
)

# print(ds.head)

ds.to_netcdf("s2_multiband.nc")
