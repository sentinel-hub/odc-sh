import xarray as xr

stored_data = xr.open_dataset("s2_multiband.nc")

print(stored_data.head)

for t in stored_data.time:
    print(f"times: {t.data}")

d = stored_data.sel(time=stored_data.time[0], bands="B1")
print(d.head)
