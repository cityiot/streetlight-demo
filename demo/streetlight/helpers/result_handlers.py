# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module containing the functions returning the data analysis results."""

import collections
import datetime

from django.db.models.query import QuerySet

import streetlight.models as models
import streetlight.helpers.constants as constants
import streetlight.helpers.data_handlers as data_handlers
import streetlight.helpers.http_helpers as http_helpers
import streetlight.helpers.time_handlers as time_handlers
import streetlight.helpers.value_holder as value_holder
import streetlight.utils as utils


def round_electricity_value(value, decimals=1):
    """Returns the given value rounded to the given number of decimals."""
    if isinstance(value, float):
        return round(value, decimals)
    if isinstance(value, value_holder.ValueHolder):
        return value.round(decimals)
    return value


def get_electricity_log(service_type: str, log_text: str, log_level: str):
    """Filters the given log text using the given log level.
       Changes the attribute name to the ones shown on the screen."""
    info_level = log_text["log_level"]
    light_info = log_text["light_info"]
    problem_info = log_text["problem_info"]
    extra_info = log_text["extra_info"]

    if (log_level == "info" or
            (log_level == "warning" and (info_level in ("Warning", "Error"))) or
            (log_level == "error" and info_level == "Error")):
        attribute_list = []
        for attribute_name in constants.ATTRIBUTES[service_type]:
            if service_type == "tampere":
                for phase in constants.PHASES:
                    short_name = constants.SHORT_ATTRIBUTE_NAMES_WITH_PHASE[(attribute_name, phase)]
                    attribute_list.append(round_electricity_value(
                        log_text["values"].get(short_name, "")))
            else:
                short_name = constants.SHORT_ATTRIBUTE_NAMES[attribute_name]
                attribute_list.append(round_electricity_value(
                    log_text["values"].get(short_name, "")))

        time_text = log_text["time"]
        if time_text == "":
            full_time_text = ""
        else:
            full_time_text = "{}-{}".format(log_text["time"], time_handlers.get_interval_end_time(log_text["time"]))
        return {
            "time": full_time_text,
            "attributes": attribute_list,
            "lights": light_info,
            "energy": log_text.get("energy", None),
            "problems": problem_info,
            "details": extra_info
        }
    return {}


def format_switch_log(log_text, log_level: str):
    """Formats the given log text using the given log level."""
    info_level = log_text["log_level"]
    if (log_level == "info" or
            (log_level == "warning" and (info_level in ("Warning", "Error"))) or
            (log_level == "error" and info_level == "Error")):
        return log_text
    return {}


def get_entity_data_header_list(service_type: str):
    """Returns the full header list and the attribute count for the given service type."""
    attribute_list = []
    for attribute_name in constants.ATTRIBUTES[service_type]:
        if service_type == "tampere":
            for phase in constants.PHASES:
                attribute_list.append(constants.SHORT_ATTRIBUTE_NAMES_WITH_PHASE[(attribute_name, phase)])
        else:
            attribute_list.append(constants.SHORT_ATTRIBUTE_NAMES[attribute_name])

    entity_data_header = ["time"] + attribute_list + \
        ["lights", "estimated energy", "problems", "average and standard deviations (from the last 3 weeks)"]
    return entity_data_header, len(attribute_list)


def get_requests_day_values_only(request_day_values: collections.OrderedDict):
    """Returns a simplified dictionary from the given request_day_values that
       does not have the limit or history information and can be used as
       existing_values parameter when fetching new values.
    """
    return collections.OrderedDict(
        (
            time_string,
            {
                attribute_name: attribute_info["value"]
                for attribute_name, attribute_info in attributes.items()
                if "value" in attribute_info
            }
        )
        for time_string, attributes in request_day_values.items()
    )


def get_light_info(area_object, streetlight_object, date_string: str, log_level: str):
    """Returns the context needed for showing the detailed information about
       a single streetlight/streetlightgroup on a specific date."""
    service_type = area_object.service_type

    switch_times = fetch_switch_times(area_object, date_string)
    switch_log_text = data_handlers.fetch_switch_time_results(streetlight_object, date_string, switch_times)
    # data_handlers.save_db_warnings(streetlight_object, date_string, switch_log_text.get("db_warnings", {}))

    entity_data_header, attribute_count = get_entity_data_header_list(service_type)
    request_day_values, estimated_attributes = data_handlers.fetch_electricity_values(streetlight_object, date_string)

    entity_name = streetlight_object.name.split(":")[-1]
    data_log_texts = [
        data_handlers.create_electricity_log_text(
            service_type,
            entity_name,
            time_string,
            electricity_values,
            switch_times,
            date_string,
            estimated_attributes
        )
        for time_string, electricity_values in request_day_values.items()]

    energy_information = fetch_energy_values(
        streetlight_object, date_string,
        get_requests_day_values_only(request_day_values), estimated_attributes
    )

    entry_list = []
    for _, log_text in enumerate(data_log_texts):
        energy_value = energy_information.get(log_text["time"], None)
        if energy_value is not None:
            log_text["energy"] = energy_value.round(1)
        new_log = get_electricity_log(service_type, log_text, log_level)
        if new_log != {}:
            entry_list.append(new_log)


    if not data_log_texts:
        entry_list = [{
            "attributes": [""] * attribute_count,
            "problems": "no information"
        }]

    # TODO: give the actual energy value from request_day_energy as parameter
    day_energy, estimated_energy_hours = get_daily_energy(streetlight_object, date_string)

    return {
        "area": area_object.name.split(":")[-1],
        "address": area_object.address.split(", ")[-1],
        "expected_switch_off": constants.TIME_INTERVAL_SEPARATOR.join(switch_times[0]),
        "expected_switch_on": constants.TIME_INTERVAL_SEPARATOR.join(switch_times[1]),
        "switch_header": [
            "switch off time", "switch on time", "off early", "off late",
            "on early", "on late", "inacc_off", "inacc_on"],
        "data_header": entity_data_header,
        "streetlight": {
            "switch": format_switch_log(switch_log_text, log_level),
            "data": {
                "entity_id": streetlight_object.name.split(":")[-1],
                "address": streetlight_object.address.split(", ")[-1],
                "full_address": streetlight_object.address,
                "entries": entry_list,
                "day_energy": {
                    "value_str": daily_energy_as_str(day_energy),
                    "estimated_hours": estimated_energy_hours
                }
            }
        }
    }


def get_all_lights_info_simple(streetlight_objects: QuerySet, date_string: str,
                               expected_switch_times: list, log_level: str, area_name=None):
    """Returns actual streetlight switch time information for all streetlight objects in the area."""
    switch_logs = data_handlers.fetch_all_switch_time_results(
        streetlight_objects, date_string, expected_switch_times, area_name=area_name, simple=True)
    streetlight_location_and_energy = [
        {
            "latitude": light.latitude,
            "longitude": light.longitude,
            "address": light.address.split(",")[-1].strip(),
            "day_energy_str": daily_energy_as_str(get_daily_energy(light, date_string)[0])
        }
        for light in streetlight_objects
    ]
    switch_logs = [
        {**switch_log, **extra_info}
        for switch_log, extra_info in zip(switch_logs, streetlight_location_and_energy)
    ]

    for index, switch_log in enumerate(switch_logs):
        switch_logs[index]["info"] = format_switch_log(switch_log["info"], log_level)
    return switch_logs


def fetch_switch_times(area: models.Area, date_string: str):
    """Returns the expected streetlight switch off and switch on times for the corresponding area and date.
       The times are given as time intervals given as tuples: (begin_time, end_time).
       Uses the times stored in the internal database if possible.
       Otherwise, loads the illuminance data from QuantumLeap and calculates the times based on loaded data.
       Updates the internal database with the calculated values."""
    date_object = time_handlers.get_dt_object(date_string).date()
    stored_time_off = models.SwitchTime.objects.filter(area=area, switch_type="off", date=date_object)
    stored_time_on = models.SwitchTime.objects.filter(area=area, switch_type="on", date=date_object)

    if stored_time_off and stored_time_on:
        switch_off_object = stored_time_off.first()
        switch_on_object = stored_time_on.first()
        return ([
            [
                time_handlers.str_from_time(time_object)
                for time_object in [switch_object.low_value, switch_object.high_value]
            ]
            for switch_object in [switch_off_object, switch_on_object]
        ])

    # no switch times found in the database => use QuantumLeap data to determine them
    switch_off, switch_on = get_switch_times(
        service_type=area.service_type,
        device_id=area.illuminance_entity,
        date_string=date_string,
        illuminance_limits={"off": area.illuminance_off, "on": area.illuminance_on})

    for switch_time, switch_type in zip([switch_off, switch_on], ["off", "on"]):
        time_handlers.store_switch_time(area, switch_time, date_object, switch_type, "area")

    return (switch_off, switch_on)


def get_switch_times(service_type: str, device_id: str, date_string: str, illuminance_limits: list):
    """Loads the illuminance information from QuantumLeap and
       calculates and returns the expected streetlight switch off and switch on times."""
    illuminance_values = http_helpers.get_illuminance_values(service_type, device_id, date_string)
    illuminances = illuminance_values.get("data", {}).get("attributes", [{}])[0].get("values", [])
    times = [time_value.split("T")[-1].split(".")[0]
             for time_value in illuminance_values.get("data", {}).get("index", [])]

    switch_info = time_handlers.determine_switch_times(date_string, illuminances, times, illuminance_limits)

    dt_now = datetime.datetime.now()
    if service_type == "tampere":
        dt_now -= datetime.timedelta(hours=12)
    date_object = time_handlers.date_from_str(date_string)

    for switch_times, limit_times in switch_info:
        for index, switch_time in enumerate(switch_times):
            if switch_time is None and date_object < dt_now.date():
                switch_time = limit_times[index]
            switch_times[index] = time_handlers.timestring_from_int(switch_time)

    return [switch_times for switch_times, _ in switch_info]


def fetch_energy_values(streetlight_object, date_string: str,
                        existing_values=None, existing_estimated_values=None):
    """Loads the energy values for the given streetlight and date from the database.
       If no values are found, tries to fetch the values from QuantumLeap."""
    time_limit_low, time_limit_high = time_handlers.get_limit_times(date_string)

    date_object = time_handlers.get_dt_object(date_string)
    check_storage = models.MeasurementStored.objects.filter(streetlight_entity=streetlight_object, date=date_object)
    if check_storage:
        request_day_storage = check_storage.first().realtime_values

        entity_measurements = models.Measurement.objects.filter(
            streetlight_entity=streetlight_object,
            value__isnull=False,
            timestamp__gte=time_limit_low,
            timestamp__lt=time_limit_high)

        if request_day_storage == "none":
            energy_values = data_handlers.get_energy_results(
                entity=streetlight_object, date_string=date_string,
                existing_values=existing_values,
                existing_estimated_attributes=existing_estimated_values
            )
        elif request_day_storage == "part":
            if existing_values is None or existing_estimated_values is None:
                existing_values, existing_estimated_values = \
                    data_handlers.parse_request_day_values(entity_measurements)
            energy_values = data_handlers.get_energy_results(
                entity=streetlight_object, date_string=date_string,
                existing_values=existing_values,
                existing_estimated_attributes=existing_estimated_values
            )
        else:
            energy_values = data_handlers.parse_energy_values(entity_measurements)

    else:
        energy_values = data_handlers.get_energy_results(
            entity=streetlight_object, date_string=date_string,
            existing_values=existing_values,
            existing_estimated_attributes=existing_estimated_values
        )

    # NOTE: the gap filling should be already done in the get and parse functions
    # energy_values = fill_gaps_in_energy_results(energy_values)
    return energy_values


def daily_energy_as_str(daily_energy: float):
    """Returns a string corresponding to the given energy changed to an appropriate unit."""
    if daily_energy < 1e3:
        return "{value:.0f} {unit:s}".format(
            value=daily_energy,
            unit="Wh")
    if daily_energy < 1e6:
        return "{value:.1f} {unit:s}".format(
            value=daily_energy / 1e3,
            unit="kWh")
    if daily_energy < 1e9:
        return "{value:.2f} {unit:s}".format(
            value=daily_energy / 1e6,
            unit="MWh")
    return "{value:.3f} {unit:s}".format(
        value=daily_energy / 1e9,
        unit="GWh")


def get_daily_energy(streetlight_object, date_string: str, energy_values=None):
    """Returns the estimated daily energy use and the estimation level for the given streetlight and date.
       If the database contains precalculated value, return that value directly.
       If the value is not yet available, does the needed calculations.
       - Uses the given hourly energy values if they are given.
       - Fetches the needed values from the database or if needed from the QuantumLeap.
       - Stores the calculated value if it corresponds to a full day.
    """
    if streetlight_object is None:
        return 0.0, 0

    date_object = time_handlers.get_dt_object(date_string).date()
    db_energy = models.DayEnergy.objects.filter(streetlight_entity=streetlight_object, date=date_object)
    if db_energy:
        db_energy = db_energy.first()
        return db_energy.value, db_energy.estimated_hours

    if not energy_values:
        energy_values = fetch_energy_values(streetlight_object, date_string)

    value_list = [
        (energy_values[time_string].value, energy_values[time_string].is_actual)
        for time_string in energy_values
    ]
    day_energy = sum([value[0] for value in value_list])
    estimated_hours = constants.HOURS_IN_DAY - sum([value[1] for value in value_list])

    if len(energy_values) == constants.HOURS_IN_DAY:
        db_energy_object = models.DayEnergy(
            streetlight_entity=streetlight_object,
            date=date_object,
            value=day_energy,
            estimated_hours=estimated_hours)
        db_energy_object.save()

    return day_energy, estimated_hours


def get_area_daily_energy(streetlight_objects: QuerySet, date_string: str):
    """Returns the total daily energy consumption for the area consisting of the given streetlights."""
    total_energy = 0.0
    if streetlight_objects:
        for streetlight_object in streetlight_objects:
            total_energy += get_daily_energy(streetlight_object, date_string)[0]
    return total_energy


def get_service_daily_energy(service_type: str, date_string: str):
    """Returns the total daily energy consumption for the entire service."""
    service_streetlights = utils.get_service_streetlights(service_type)
    print("Found {} streetlights in {}.".format(str(len(service_streetlights)), service_type), flush=True)
    return get_area_daily_energy(service_streetlights, date_string)


def get_missing_data_warnings(request_day_values, estimated_attributes):
    """Returns a dictionary containing boolean warning flag related to missing data based on the input data."""
    not_connected = True
    missing_data_one = False
    missing_data_half = False

    missing_count = 0
    time_string_count = len(request_day_values)
    for time_string, attributes in request_day_values.items():
        estimated_attr_for_time = estimated_attributes.get(time_string, [])

        full_attribute_names = []
        for attribute_name, attribute_value in attributes.items():
            if isinstance(attribute_value, dict):
                for sub_attr_name, sub_attr_value in attribute_value.items():
                    full_attr_name = ".".join([attribute_name, sub_attr_name])
                    if attribute_name == constants.ENERGY_ATTRIBUTE:
                        full_attribute_names.append(attribute_name)
                        if (sub_attr_value is not None and data_handlers.check_for_estimation_level(
                                estimated_attr_for_time, attribute_name) >= constants.ESTIMATION_LIMIT_LOW):
                            not_connected = False
                    else:
                        full_attribute_names.append(full_attr_name)
                        if (sub_attr_value is not None and data_handlers.check_for_estimation_level(
                                estimated_attr_for_time, full_attr_name) >= constants.ESTIMATION_LIMIT_LOW):
                            not_connected = False
            else:
                full_attribute_names.append(attribute_name)
                if (attribute_value is not None and data_handlers.check_for_estimation_level(
                        estimated_attr_for_time, attribute_name) >= constants.ESTIMATION_LIMIT_LOW):
                    not_connected = False

        if not set(full_attribute_names) - {est_attr_name for est_attr_name, _ in estimated_attr_for_time}:
            missing_count += 1
            missing_data_one = True
            if missing_count >= time_string_count / 2:
                missing_data_half = True

        if not not_connected and missing_data_one and missing_data_half:
            break

    print("----------============------------", flush=True)
    print(request_day_values, flush=True)
    print(estimated_attributes, flush=True)
    print(not_connected, missing_data_one, missing_data_half, flush=True)

    return {
        "not_connected": not_connected,
        "missing_data_one": missing_data_one,
        "missing_data_half": missing_data_half,
    }


def get_db_warnings(streetlight_object, date_string: str):
    """Returns a warning object for the given streetlight and date.
       If the object cannot be found, then the appropriate data is fetched and
       the warning flags are saved to the database before returning the object.
       Returns None, if the flag determination failed.
    """
    date_object = time_handlers.get_dt_object(date_string).date()
    found_warnings = models.DateWarning.objects.filter(streetlight_entity=streetlight_object, date=date_object)
    if found_warnings:
        return found_warnings.first()

    switch_times = fetch_switch_times(streetlight_object.area1, date_string)
    switch_info = data_handlers.fetch_switch_time_results(streetlight_object, date_string, switch_times, True)

    request_day_values, estimated_attributes = data_handlers.get_electricity_results_realtime(
        entity=streetlight_object, date_string=date_string)
    missing_data_warnings = get_missing_data_warnings(request_day_values, estimated_attributes)

    data_handlers.save_db_warnings(
        streetlight_object,
        date_string,
        {**switch_info.get("db_warnings", {}), **missing_data_warnings})

    found_warnings = models.DateWarning.objects.filter(streetlight_entity=streetlight_object, date=date_object)
    if found_warnings:
        return found_warnings.first()
    return None


def is_no_warnings_set(warning_object: models.DateWarning):
    """Returns True, if no warnings are set in the given object."""
    if (warning_object is None or
            warning_object.not_connected or
            warning_object.missing_data_one or
            warning_object.missing_data_half or
            warning_object.wrong_switch_off_time or
            warning_object.wrong_switch_on_time):
        return False
    return True
