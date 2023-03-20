from datetime import datetime
from typing import Any, Dict, List

from sentinelhub import DataCollection, SentinelHubRequest, MosaickingOrder, ResamplingType, parse_time


def features_to_dates(features: List[Dict[str, Any]]):
    """
    Convert list of features from SH Catalog into list of timestamps.
    :param features: Tile dictionaries as returned by SH WFS
    :return: List timestamps.
    """
    timestamps = []
    for feature in features:
        properties = feature["properties"]
        time = properties["datetime"]
        try:
            dt = datetime.combine(parse_time(time).date(), datetime.min.time())
            timestamps.append(dt)
        except ValueError as e:
            print(f"failed parsing datetime variable: {e}")

    timestamps = sorted(set(timestamps))
    return timestamps


def get_evalscript(band_names, band_units, band_sample_types=None):
    responses_element = []
    for band_name in band_names:
        responses_element.append(
            {
                "identifier": band_name if len(band_names) > 1 else "default",
                "format": {"type": "image/tiff"},
            }
        )

    evalscript = []
    evalscript.extend(
        [
            " //VERSION=3 ",
            " function setup() {",
            "    return {",
        ]
    )
    if band_units:
        band_names_str = ", ".join(map(repr, band_names))
        band_units_str = ", ".join(map(repr, band_units))
        evalscript.extend(
            [
                "        input: [{",
                "            bands: [" + band_names_str + "],",
                "            units: [" + band_units_str + "],",
                "        }],",
            ]
        )
    else:
        evalscript.extend(
            [
                "        input: [" + ", ".join(map(repr, band_names)) + "],",
            ]
        )
    evalscript.extend(
        [
            "   output: [",
        ]
    )
    if len(band_names) > 1:
        evalscript.extend(
            [
                "  {id: "
                + repr(band_name)
                + ", bands: 1, sampleType: "
                + repr(sample_type)
                + "},"
                for band_name, sample_type in zip(band_names, band_sample_types)
            ]
        )
    else:
        evalscript.extend(
            ["            {bands: 1, sampleType: " + repr(band_sample_types[0]) + "}"]
        )

    evalscript.extend(["        ]", "    };", "}"])
    if len(band_names) > 1:
        evalscript.extend(
            [
                " function evaluatePixel(sample) {",
                "    return {",
            ]
        )
        evalscript.extend(
            [
                "        " + band_name + ": [" + " sample." + band_name + "],"
                for band_name in band_names
            ]
        )
        evalscript.extend(
            [
                "    };",
                "}",
            ]
        )
    else:
        evalscript.extend(
            [
                " function evaluatePixel(sample) {",
                "    return [sample." + band_names[0] + "];",
                "}",
            ]
        )

    eval_str = " \n".join(evalscript)
    return eval_str, responses_element


def build_sentinel_hub_request(
    config, collection, date, size, bbox, evalscript, responses, resempling, maxcc
):
    return SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=collection,
                time_interval=(f"{date}T00:00:00Z", f"{date}T23:59:59Z"),
                mosaicking_order=MosaickingOrder.MOST_RECENT,
                upsampling=resempling,
                downsampling=resempling,
                maxcc=maxcc
            )
        ],
        responses=responses,
        bbox=bbox,
        size=size,
        config=config,
    )


def get_catalog_results(catalog, product, bbox, time_interval):
    """Gets the image metadata the SH REST API.
    param: catalog: Sentinelhub.SentinelHubCatalog instance.
    param product: name of the collection catalog_id we are searching for
    param bbox: Sentinelhub.BBox
    Returns: The iterable result of obrained images metadata from the Sentinel HUB catalog API.
    """

    parameters = dict(
        collection=product,
        bbox=bbox,
        time=(f"{time_interval[0]}T00:00:00", f"{time_interval[1]}T23:59:59"),
    )
    return catalog.search(**parameters)


def getCollection(collection_id, sh_filter=None):
    for col in DataCollection.get_available_collections():
        if col.api_id != collection_id:
            continue

        if not sh_filter:
            return col

        filters_match = all(
            getattr(col, key) == value for key, value in sh_filter.items()
        )
        if filters_match:
            return col

    raise ValueError(
        f"Collection with id {collection_id} and filter {sh_filter} doesn't exist"
    )
