# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module containing helper functions for making http queries to FIWARE platform."""

import datetime
import requests

import streetlight.helpers.constants as constants
import streetlight.helpers.datetime_builder as dt_builder
import streetlight.helpers.time_handlers as time_handlers
import streetlight.helpers.value_handlers as value_handlers

HTTP_TIMEOUT = 30.0


def http_address(path_parts: list, query_params: dict):
    """Returns the constructed http address.

    :param path_parts: the path of the address given as a list
    :param query_params: the query parameters given as a dictionary
    :returns the constructed http address
    """
    query_strings = []
    for query_param_name, query_param_value in query_params.items():
        query_strings.append("=".join([query_param_name, str(query_param_value)]))

    return "?".join([
        "/".join(path_parts),
        "&".join(query_strings)
    ])


def get_headers(service_type: str):
    """Returns the service specific headers used with FIWARE queries.

    :param service_type: the streetlight data service (tampere/viinikka)
    :returns the http headers
    """
    return constants.FIWARE_HEADERS.get(service_type, {})


def get_illuminance_id(service_type: str, device_id: str):
    """Returns the entity id from which the illuminance attribute is read."""
    if service_type == "tampere":
        if device_id == constants.EXTRA_CABINET[service_type]:
            return constants.DEFAULT_ILLUMINANCE_DEVICE[service_type]
        return ":".join([get_illuminance_type(service_type), device_id.split(":")[-1]])
    if service_type == "viinikka":
        return constants.DEFAULT_ILLUMINANCE_DEVICE[service_type]
    return device_id


def get_illuminance_type(service_type: str):
    """Returns the entity type from which the illuminance attribute is read."""
    if service_type == "tampere":
        return "WeatherObserved"
    return "AmbientLightSensor"


def illuminance_address(device_id: str, date_string: str):
    """Returns the http query address for getting illuminance information from QuantumLeap."""
    year, month, day = [int(part) for part in date_string.split("-")]
    limit_hour = time_handlers.get_limit_hour(
        time_handlers.get_time_season(time_handlers.get_dt_object(date_string)))
    extra_day = 1 if limit_hour > 0 else 0
    previous_date = (datetime.datetime(year=year, month=month, day=day) - datetime.timedelta(days=extra_day))

    start_time = "{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00.000Z".format(
        year=previous_date.year,
        month=previous_date.month,
        day=previous_date.day,
        hour=limit_hour
    )
    end_time = "{year:04d}-{month:02d}-{day:02d}T{hour:02d}:59:59.999Z".format(
        year=year, month=month, day=day, hour=(limit_hour + 23) % 24
    )

    return http_address(
        [constants.QUANTUMLEAP_ADDRESS, "entities", device_id],
        {
            "attrs": "illuminance",
            "fromDate": start_time,
            "toDate": end_time,
            "aggrMethod": "avg",
            "aggrPeriod":  "minute"
        })


def streetlight_address(entity_id: str, request_date: datetime, history_days: int, attributes: list, **kwargs):
    """Constructs and returns the http query address for getting streetlight specific information
       from QuantumLeap using the /entities endpoint.

    Args:
        entity_id: the id string for the FIWARE entity
        request_date: the datetime object corresponding to the selected date
        history_days: the number of days used for the determineng the historical trends for values
        attributes: list containing the attribute names
        strict_start_date: datetime object corresping to the beginning of the time interval (default: None)
        use_aggregation: whether to use aggregation method avg (default: False)
        time_interval_s: the value for aggrPeriod, ignored if use_aggregation is False (default: 1)

    Returns:
        The constructed http query string
    """
    limit_hour = time_handlers.get_limit_hour(time_handlers.get_time_season(request_date))
    extra_day = 1 if limit_hour > 0 else 0
    start_date = (request_date - datetime.timedelta(days=history_days + extra_day))

    strict_start_date = kwargs.get("strict_start_date", None)
    if strict_start_date:
        start_date = max(start_date, strict_start_date)
        start_time_parts = (start_date.hour, start_date.minute, start_date.second)
    else:
        start_time_parts = (limit_hour, 0, 0)

    start_time = "{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z".format(
        year=start_date.year, month=start_date.month, day=start_date.day,
        hour=start_time_parts[0], minute=start_time_parts[1], second=start_time_parts[2]
    )

    end_time = "{year:04d}-{month:02d}-{day:02d}T{hour:02d}:59:59.999Z".format(
        year=request_date.year, month=request_date.month, day=request_date.day,
        hour=(limit_hour + 23) % 24
    )

    if start_time > end_time:
        return None

    attribute_string = ",".join([attribute.lower() for attribute in attributes])
    query_params = {
        "attrs": attribute_string,
        "fromDate": start_time,
        "toDate": end_time,
        "limit": str(constants.SIZE_LIMIT)
    }
    if kwargs.get("use_aggregation", False):
        time_interval_s = kwargs.get("time_interval_s", 1)
        if time_interval_s >= 3600:
            aggr_period = "hour"
        elif time_interval_s >= 60:
            aggr_period = "minute"
        else:
            aggr_period = "second"

        query_params["aggrMethod"] = "avg"
        query_params["aggrPeriod"] = aggr_period

    return http_address([constants.QUANTUMLEAP_ADDRESS, "entities", entity_id], query_params)


def streetlight_type_address(entity_type: str, request_date: datetime, history_days: int,
                             attribute_name: str, **kwargs):
    """Constructs and returns the http query address for getting streetlight specific information
       from QuantumLeap using the /types endpoint.

    Args:
        entity_type: the id string for the FIWARE entity type
        request_date: the datetime object corresponding to the selected date
        history_days: the number of days used for the determineng the historical trends for values
        attributes: list containing the attribute names
        strict_start_date: datetime object corresping to the beginning of the time interval (default: None)
        use_aggregation: whether to use aggregation method avg (default: False)
        time_interval_s: the value for aggrPeriod, ignored if use_aggregation is False (default: 1)

    Returns:
        The constructed http query string
    """
    limit_hour = time_handlers.get_limit_hour(time_handlers.get_time_season(request_date))
    extra_day = 1 if limit_hour > 0 else 0
    start_date = (request_date - datetime.timedelta(days=history_days + extra_day))

    strict_start_date = kwargs.get("strict_start_date", None)
    if strict_start_date is None:
        start_time = "{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00.000Z".format(
            year=start_date.year,
            month=start_date.month,
            day=start_date.day,
            hour=limit_hour
        )
    else:
        start_date = max(start_date, strict_start_date)
        start_time = "{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z".format(
            year=start_date.year,
            month=start_date.month,
            day=start_date.day,
            hour=start_date.hour,
            minute=start_date.minute,
            second=start_date.second
        )

    end_time = "{year:04d}-{month:02d}-{day:02d}T{hour:02d}:59:59.999Z".format(
        year=request_date.year,
        month=request_date.month,
        day=request_date.day,
        hour=(limit_hour + 23) % 24
    )

    query_params = {
        "fromDate": start_time,
        "toDate": end_time,
        "limit": str(constants.SIZE_LIMIT),
        "offset": kwargs.get("offset", 0)
    }
    if kwargs.get("use_aggregation", None):
        time_interval_s = kwargs.get("time_interval_s", 1)
        if time_interval_s >= 3600:
            aggr_period = "hour"
        elif time_interval_s >= 60:
            aggr_period = "minute"
        else:
            aggr_period = "second"

        query_params["aggrMethod"] = "avg"
        query_params["aggrPeriod"] = aggr_period

    if "entity_ids" in kwargs:
        query_params["id"] = ",".join(kwargs["entity_ids"])

    return http_address(
        [constants.QUANTUMLEAP_ADDRESS, "types", entity_type, "attrs", attribute_name],
        query_params
    )


def get_quantumleap_values(service_type: str, address: str):
    """Returns the QuantumLeap response corresponding to the given query."""
    try:
        print(address, flush=True)
        req = requests.get(address, headers=get_headers(service_type), timeout=HTTP_TIMEOUT)

        if req.status_code != 200:
            print("Received status code:", req.status_code, "({})".format(req.text), flush=True)
            return {}
        return req.json()

    except requests.exceptions.RequestException as error:
        print(error, flush=True)
        return {}


def get_illuminance_values(service_type: str, device_id: str, date_string: str):
    """Returns the QuantumLeap response when querying for illuminance values."""
    return get_quantumleap_values(service_type, illuminance_address(device_id, date_string))


def get_area_attribute(service_type: str):
    """Returns the streetlight control area entity type for the selected service."""
    if service_type == "tampere":
        return "refStreetlightCabinetController"
    return "refStreetlightControlCabinet"


def get_streetlight_type(service_type: str):
    """Returns the streetlight entity type for the selected service."""
    if service_type == "tampere":
        return "StreetlightGroup"
    return "Streetlight"


def get_streetlights(service_type: str, area_id: str):
    """Returns the Orion entities for the given streetlight service and area."""
    if area_id == constants.EXTRA_CABINET[service_type]:
        if service_type == "tampere":
            attribute_query = "==".join([get_area_attribute(service_type), "%27%27"])
        else:
            attribute_query = "".join(["!", get_area_attribute(service_type)])
    else:
        attribute_query = "~=".join([get_area_attribute(service_type), area_id])

    streetlights_address = http_address(
        [constants.ORION_ADDRESS, "entities"],
        {
            "type": get_streetlight_type(service_type),
            "limit": "1000",
            "q": attribute_query
        })

    try:
        print(streetlights_address, flush=True)
        req = requests.get(streetlights_address, headers=get_headers(service_type), timeout=HTTP_TIMEOUT)
        if req.status_code != 200:
            print("received status code:", req.status_code, flush=True)
            data = []
        else:
            data = req.json()
    except requests.exceptions.RequestException as error:
        print(error, flush=True)
        data = []

    return data


def get_latest_orion_timestamps(service_type: str, entities=None):
    """Returns a dictionary containing the latest timestamp (as datetime object) for each streetlight entity."""
    orion_address = http_address(
        [constants.ORION_ADDRESS, "entities"],
        {
            "type": get_streetlight_type(service_type),
            "attrs": ",".join(constants.FULL_STREETLIGHT_ATTRIBUTES[service_type]),
            "metadata": constants.ORION_METADATA_TIMESTAMP_ATTRIBUTE,
            "limit": 1000
        })

    data = {}
    try:
        print(orion_address, flush=True)
        req = requests.get(orion_address, headers=get_headers(service_type), timeout=HTTP_TIMEOUT)
        if req.status_code != 200:
            print("received status code:", req.status_code, flush=True)
        else:
            for entity in req.json():
                if entities and entity["id"] not in entities:
                    continue
                data[entity["id"]] = value_handlers.compare([
                    dt_builder.DatetimeBuilder.get_object(
                        attribute_value["metadata"][constants.ORION_METADATA_TIMESTAMP_ATTRIBUTE]["value"]
                        .split(".")[0])
                    for attribute_name, attribute_value in entity.items()
                    if ("metadata" in attribute_value and
                        constants.ORION_METADATA_TIMESTAMP_ATTRIBUTE in attribute_value["metadata"])], max)

    except requests.exceptions.RequestException as error:
        print(error, flush=True)

    if entities:
        for entity_name in entities:
            if entity_name not in data:
                data[entity_name] = None

    return data


def get_latest_orion_values(service_type: str, entity_name: str, attributes: list):
    """Returns the latest values for the given entity and attributes from Orion."""
    orion_address = http_address(
        [constants.ORION_ADDRESS, "entities"],
        {
            "id": entity_name,
            "type": get_streetlight_type(service_type),
            "attrs": ",".join(attributes),
            "metadata": constants.ORION_METADATA_TIMESTAMP_ATTRIBUTE
        })

    data = []
    try:
        print(orion_address, flush=True)
        req = requests.get(orion_address, headers=get_headers(service_type), timeout=HTTP_TIMEOUT)
        if req.status_code != 200:
            print("received status code:", req.status_code, flush=True)
        else:
            for entity in req.json():
                if entity["id"] != entity_name:
                    continue
                for attribute_name, attribute_value in entity.items():
                    if attribute_name in ("id", "type"):
                        continue

                    timestamp = attribute_value.get("metadata", {}).get("timestamp", {}).get("value", None)
                    if timestamp is not None:
                        timestamp = dt_builder.DatetimeBuilder.get_object(timestamp.split(".")[0])
                    value = attribute_value.get("value", None)
                    if isinstance(value, float):
                        value = round(value, 3)
                    if isinstance(value, dict):
                        for subattr_name, subattr_value in value.items():
                            if isinstance(subattr_value, float):
                                value[subattr_name] = round(subattr_value, 3)

                    data.append({
                        "name": constants.LONG_ATTRIBUTE_NAMES.get(attribute_name, attribute_name),
                        "value": value,
                        "timestamp": timestamp
                    })
    except requests.exceptions.RequestException as error:
        print(error, flush=True)

    return data


def get_areas():
    """Returns al the control area and streetlight information from Orion."""
    area_address = http_address(
        [constants.ORION_ADDRESS, "entities"],
        {"type": "StreetlightControlCabinet", "limit": 1000})

    service_types = ["tampere", "viinikka"]
    areas = {}
    for service_type in service_types:

        try:
            print(area_address, flush=True)
            req = requests.get(area_address, headers=get_headers(service_type), timeout=HTTP_TIMEOUT)

            if req.status_code != 200:
                print("received status code:", req.status_code)
                continue
            data = req.json()
            data += [{}]

            for data_element in data:
                area_id = data_element.get("id", constants.EXTRA_CABINET[service_type])
                # ignore the old Viinikka ids
                if service_type == "viinikka" and (":tampere:" in area_id or "90FD9FFFFEDA5A05" in area_id):
                    continue

                streetlight_entities = get_streetlights(service_type, area_id)

                new_streetlights = []
                for streetlight_entity in streetlight_entities:
                    if service_type == "viinikka" and ":" in streetlight_entity["id"]:
                        continue

                    streetlight_location = streetlight_entity.get("location", {}).get("value", {})
                    if service_type == "tampere":
                        # the old system coordinates are in the wrong order
                        streetlight_location["coordinates"] = list(reversed(streetlight_location["coordinates"]))

                    new_streetlights.append({
                        "id": streetlight_entity["id"],
                        "type": streetlight_entity["type"],
                        "address": streetlight_entity.get("address", {}).get("value", {}),
                        "location": streetlight_location
                    })

                area_location = data_element.get("location", {}).get("value", {})
                if service_type == "tampere" and "coordinates" in area_location:
                    # the old system coordinates are in the wrong order
                    area_location["coordinates"] = list(reversed(area_location["coordinates"]))

                areas[area_id] = {
                    "id": area_id,
                    "service_type": service_type,
                    "address": data_element.get("address", {}).get("value", {}),
                    "location": area_location,
                    "illuminance_limits": {
                        "off": data_element.get("illuminanceOff", {}).get("value", constants.DEFAULT_ILLUMINANCE_OFF),
                        "on": data_element.get("illuminanceOn", {}).get("value", constants.DEFAULT_ILLUMINANCE_ON)
                    },
                    "illuminance_entity": get_illuminance_id(service_type, area_id),
                    "streetlights": new_streetlights
                }

        except requests.exceptions.RequestException as error:
            print(error, flush=True)

    return areas
