from sentinelhub import DataCollection

from odc_sh import engine

dc = engine.Datacube()

p = dc.list_products()

resolution = 100  # in meters
longitude = (11.987527, 13.704914)
latitude = (41.590797, 42.218348)

time = ("2019-01-01", "2019-01-04")

dc.list_products

ds = dc.load(
    product=DataCollection.SENTINEL2_L1C.api_id,
    latitude=latitude,
    longitude=longitude,
    time=time,
    sh_resolution=resolution,
)

ds.to_netcdf("s2_all_bands.nc")
