import rasterio
import xarray as xr
from rasterio.transform import Affine

nc_file_name = "s2_multiband.nc"

stored_data = xr.open_dataset(nc_file_name)
stored_data = stored_data.__xarray_dataarray_variable__

print("Data structure")
print(stored_data.head)

single_timeframe = stored_data.sel(time="2019-01-01", drop=True)

x_res = (max(single_timeframe.lon.values) - min(single_timeframe.lon.values)) / len(
    single_timeframe.lon.values
)

y_res = (max(single_timeframe.lat.values) - min(single_timeframe.lat.values)) / len(
    single_timeframe.lat.values
)

transform = Affine.translation(
    min(single_timeframe.lon.values), min(single_timeframe.lat.values)
) * Affine.scale(x_res, y_res)

out_file_name = nc_file_name.replace(".nc", ".tif")

# define rgb bands
bands = [
    "B04",
    "B03",
    "B02",
]

dataset = rasterio.open(
    out_file_name,
    "w",
    driver="GTiff",
    height=single_timeframe.shape[0],
    width=single_timeframe.shape[1],
    count=len(bands),
    dtype=single_timeframe.data.dtype,
    crs="+proj=latlong",
    transform=transform,
)

for idx, band in enumerate(bands):
    print(f"Writting band {band} - {idx+1}")
    d = single_timeframe.sel(bands=band, drop=True).data
    dataset.write(d, idx + 1)

dataset.close()

print(f"Created file {out_file_name}")
