from sentinelhub import SHConfig
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from odc_sh import SentinelHubCommercialData
from odc_sh import Providers, AirbusConstellation, ThumbnailType, WorldViewKernel, WorldViewSensor, SkySatType, SkySatBundle, ScopeType, ScopeBundle
import pandas as pd
import numpy as np
from shapely.geometry import box
import os
import json
import shapely


sh_client_id=""
sh_client_secret=""

if not sh_client_id:
    sh_client_id = os.environ['SH_CLIENT_ID']

if not sh_client_secret:
    sh_client_secret = os.environ['SH_CLIENT_SECRET']


config = SHConfig()
config.sh_client_id = sh_client_id
config.sh_client_secret = sh_client_secret


shcd = SentinelHubCommercialData(config)

time_from = "2017-05-25T00:00:00Z"
time_to = "2018-10-25T23:59:59Z"

bounds = [
  12.742243,
  42.05043,
  12.746302,
  42.053218
]


res = shcd.search_airbus(AirbusConstellation.SPOT, bounds, time_from, time_to, maxCloudCoverage=90, maxSnowCoverage=50)

# Optional parameters: 
#    - props
#
# example: res.print_info(props=["id", "acquisitionDate", "resolution", "cloudCover"])
res.print_info()

# Getting ids
item_ids = res.get_ids()