from sentinelhub import DataCollection

from odc_sh import engine

dc = engine.Datacube()

p = dc.list_products()

resolution = 100  # in meters
longitude = (12.181599, 14.878371)
latitude = (44.687271, 45.064587)

time = ("2019-01-01", "2019-01-04")

dc.list_products

ds = dc.load(
    product=DataCollection.SENTINEL2_L1C.api_id,
    measurements=["B01"],
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
)

# print(ds.head)

ds.to_netcdf("s2_single_band.nc")
