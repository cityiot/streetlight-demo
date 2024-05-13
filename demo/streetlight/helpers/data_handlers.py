# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module containing helper functions for data handling."""

import collections
# import copy
import datetime
import statistics
import typing

from django.db.models.query import QuerySet

import streetlight.models as models
import streetlight.helpers.constants as constants
import streetlight.helpers.http_helpers as http_helpers
import streetlight.helpers.time_handlers as time_handlers
import streetlight.helpers.value_handlers as value_handlers
import streetlight.helpers.value_holder as value_holder
import streetlight.utils as utils


def ql_data_initial_parsing(streetlight_data_list: list):
    """Does the initial parsing for QuantumLeap data (combine time and data values)."""
    data_values = []
    start_index = 0
    for streetlight_data in streetlight_data_list:
        for time_value in streetlight_data.get("index", []):
            data_values.append((time_value, {}))

        for attribute in streetlight_data.get("attributes", []):
            attribute_name = attribute.get("attrName", "")
            if attribute_name != "":
                for index, attribute_value in enumerate(attribute.get("values", []), start=start_index):
                    data_values[index][1][attribute_name] = attribute_value

        start_index = len(data_values)

    return data_values


def ql_data_separation(data_values: list, history_limit: datetime.datetime, time_interval_s: int):
    """Separates the QuantumLeap data to the request date data and historical data."""
    request_day_data = collections.OrderedDict()
    history_data = {}

    for time_value, data_value in data_values:
        datetime_value = time_handlers.get_dt_object(time_value)
        hour = datetime_value.hour
        time_string_interval = time_handlers.get_time_interval_start(
            str(datetime_value.time()), time_interval_s, time_handlers.get_time_season(datetime_value))

        for attribute_name, attribute_value in data_value.items():
            if value_handlers.value_outside_limits(attribute_name, attribute_value):
                continue
            if attribute_name not in history_data:
                history_data[attribute_name] = value_handlers.get_empty_history_dict()
            if datetime_value < history_limit:
                history_data[attribute_name][hour]["raw"].append(attribute_value)
            else:
                value_handlers.add_attribute_value(
                    request_day_data, time_string_interval, attribute_name, attribute_value)

    return request_day_data, history_data


def ql_type_data_separation(streetlight_data: dict, history_limit: datetime.datetime, time_interval_s: int):
    """Separates the QuantumLeap data from /types endpoint to the request date data and historical data."""
    request_day_data = {}
    history_data = {}
    for entity_id, attributes in streetlight_data.items():
        if entity_id not in request_day_data:
            request_day_data[entity_id] = collections.OrderedDict()
        if entity_id not in history_data:
            history_data[entity_id] = {}

        for attribute_name, time_values in attributes.items():
            if attribute_name not in history_data[entity_id]:
                history_data[entity_id][attribute_name] = value_handlers.get_empty_history_dict()

            for time_index, attribute_value in time_values.items():
                if value_handlers.value_outside_limits(attribute_name, attribute_value):
                    continue
                datetime_value = time_handlers.get_dt_object(time_index)
                if datetime_value < history_limit:
                    hour = datetime_value.hour
                    history_data[entity_id][attribute_name][hour]["raw"].append(attribute_value)
                else:
                    time_string = time_handlers.get_time_interval_start(
                        str(datetime_value.time()), time_interval_s, time_handlers.get_time_season(datetime_value))
                    value_handlers.add_attribute_value(
                        request_day_data[entity_id], time_string, attribute_name, attribute_value)

    return request_day_data, history_data


def handle_streetlight_data(streetlight_data_list: list, request_date: datetime.datetime, time_interval_s: int):
    """Parses the given streetlight data (from QuantumLeap using entities/ endpoint) for a single streetlight object.
       Returns the handled data as a tuple separated in request day data and historical data."""
    history_limit = request_date.replace(hour=0, minute=0, second=0, microsecond=0)
    limit_hour = time_handlers.get_limit_hour(time_handlers.get_time_season(request_date))
    if limit_hour > 0:
        history_limit -= datetime.timedelta(hours=24 - limit_hour)

    data_values = ql_data_initial_parsing(streetlight_data_list)
    request_day_data, history_data = ql_data_separation(data_values, history_limit, time_interval_s)
    value_handlers.ql_handle_history_data(history_data)
    value_handlers.ql_handle_request_day_data(request_day_data)

    return request_day_data, history_data


def handle_type_streetlight_data(streetlight_data: dict, request_date: datetime.datetime, time_interval_s: int):
    """Parses the given streetlight data (from QuantumLeap using types/ endpoint) for a single streetlight object.
       Returns the handled data as a tuple separated in request day data and historical data."""
    history_limit = request_date.replace(hour=0, minute=0, second=0, microsecond=0)
    limit_hour = time_handlers.get_limit_hour(time_handlers.get_time_season(request_date))
    if limit_hour > 0:
        history_limit -= datetime.timedelta(hours=24 - limit_hour)

    request_day_data, history_data = ql_type_data_separation(streetlight_data, history_limit, time_interval_s)
    for _, entity_history_data in history_data.items():
        value_handlers.ql_handle_history_data(entity_history_data)
    for _, entity_request_day_data in request_day_data.items():
        value_handlers.ql_handle_request_day_data(entity_request_day_data)

    return request_day_data, history_data


def combine_type_with_history(service_type: str, request_day_values: dict, history_values: dict):
    """Combines the history data to the request day data (data from /types endpoint)
       along with the calculated limit values."""
    for entity_id in request_day_values:
        value_handlers.combine_with_history(
            service_type, request_day_values[entity_id], history_values[entity_id])


def get_history_info(attribute_value: dict):
    """Returns statistical history information as a string."""
    avg = attribute_value.get("history", {}).get("avg", "null")
    stdev = attribute_value.get("history", {}).get("stdev", "null")
    if avg == "null" or stdev == "null":
        return ""

    if isinstance(avg, float):
        avg = round(avg, 1)
    if isinstance(avg, dict):
        # todo add rounding to 1 decimal
        avg = ";".join([str(avg.get(phase, "")) for phase in constants.PHASES])

    if isinstance(stdev, float):
        stdev = round(stdev, 1)
    if isinstance(stdev, dict):
        # todo add rounding to 1 decimal
        stdev = ";".join([str(stdev.get(phase, "")) for phase in constants.PHASES])
    return "(avg={avg:}, std={stdev:})".format(avg=avg, stdev=stdev)


def attribute_value_check(service_type: str, switch_checks: tuple, attribute_name: str, attribute_value: dict):
    """Checks the given attribute value and returns the information from the analysis."""
    if service_type == "tampere" and attribute_name == "voltage":
        return "", "", get_history_info(attribute_value)

    light_info = value_handlers.get_light_status(attribute_value)

    switch_off_check, switch_on_check = switch_checks
    info_level = ""
    extra_info = get_history_info(attribute_value)
    if extra_info is None:
        extra_info = ""

    if switch_off_check < 0 or switch_on_check > 0:
        if light_info != "off":
            if attribute_name in constants.ATTRIBUTES_FOR_HISTORY_COMPARISON:
                if value_handlers.value_within_limits(attribute_value):
                    info_level = "Ok"
                else:
                    info_level = "Warning"
            else:
                info_level = "Ok"
        else:
            info_level = time_handlers.get_time_info(switch_off_check, switch_on_check)[0]

    elif switch_off_check > 0 and switch_on_check < 0:
        if light_info != "off":
            info_level = time_handlers.get_time_info(switch_off_check, switch_on_check)[0]
        else:
            if attribute_name in constants.ATTRIBUTES_FOR_HISTORY_COMPARISON:
                if value_handlers.value_within_limits(attribute_value):
                    info_level = "Ok"
                else:
                    info_level = "Warning"
            else:
                info_level = "Ok"

    else:
        info_level = "Ok"

    if info_level == "Ok" and value_handlers.value_outside_limits(attribute_name, attribute_value):
        info_level = "Warning"

    return info_level, light_info, extra_info


def get_data_from_quantumleap(service_type: str, entity_id: str, check_date: datetime.datetime,
                              attributes: list, **kwargs):
    """Fetches QuantumLeap data for the selected entity, attributes and date using the /entities endpoint."""
    result_list = []
    start_date = kwargs.get("strict_start_date", None)
    while True:
        check_address = http_helpers.streetlight_address(
            entity_id,
            check_date,
            kwargs.get("history_days", 0),
            attributes,
            strict_start_date=start_date,
            use_aggregation=kwargs.get("use_aggregation", False),
            time_interval_s=kwargs.get("time_interval_s", 1))

        if check_address is None:
            data = {}
        else:
            http_result = http_helpers.get_quantumleap_values(service_type, check_address)
            if "data" in http_result:
                data = http_result.get("data", {})
            else:
                data = http_result
        time_index = data.get("index", [])
        if not time_index:
            break

        result_list.append(data)
        if len(time_index) < constants.SIZE_LIMIT:
            break

        start_date = time_handlers.get_dt_object(time_index[-1]) + datetime.timedelta(seconds=1)

    return result_list


def add_ql_type_data_to_dict(old_values: dict, received_entities: list, attribute_name: str):
    """Adds received entity values (from /types endpoint) to the dictionary containing the old values.
       Returns a count for how many entries were found."""
    time_index_count = 0
    for received_entity in received_entities:
        received_entity_id = received_entity.get("entityId", None)
        if received_entity_id is None:
            continue

        values = received_entity.get("values", [])
        time_index_list = received_entity.get("index", [])
        time_index_count += len(time_index_list)

        if received_entity_id not in old_values:
            old_values[received_entity_id] = {}
        if attribute_name not in old_values[received_entity_id]:
            old_values[received_entity_id][attribute_name] = {}

        entity_values = {
            time_index: value
            for time_index, value in zip(time_index_list, values)
            if value is not None
        }
        old_values[received_entity_id][attribute_name] = \
            {**old_values[received_entity_id][attribute_name], **entity_values}

    return time_index_count


def get_type_data_from_quantumleap(service_type: str, entity_type: str, check_date: datetime.datetime,
                                   attributes: list, **kwargs):
    """Fetches data from QuantumLeap using the /types endpoint."""
    results = {}
    for attribute_name in attributes:
        offset = kwargs.get("offset", 0)
        while True:
            check_address = http_helpers.streetlight_type_address(
                entity_type,
                check_date,
                kwargs.get("history_days", 0),
                attribute_name,
                offset=offset,
                use_aggregation=kwargs.get("use_aggregation", False),
                time_interval_s=kwargs.get("time_interval_s", 1),
                entity_ids=kwargs.get("entity_ids", None))

            http_result = http_helpers.get_quantumleap_values(service_type, check_address)
            if "data" in http_result:
                data = http_result.get("data", {})
            else:
                data = http_result
            if data.get("attrName", "") != attribute_name or data.get("entityType", "") != entity_type:
                break

            received_entities = data.get("entities", [])
            time_index_count = add_ql_type_data_to_dict(results, received_entities, attribute_name)
            if time_index_count < constants.SIZE_LIMIT:
                break

            offset += time_index_count

    return results


def contains_all_phases(values: dict):
    """Returns True, if the given value contains all 3 phases (L1, L2, L3)."""
    if values is None or not isinstance(values, dict):
        return False
    return None not in [values.get(phase, None) for phase in constants.PHASES]


def check_if_energy_is_estimate(attribute_list: list, estimated_attributes: list):
    """Checks whether any of the attributes in attribute_list are included in estimated_attributes.
       If they are, then energy will also be included in estimated_attributes."""
    if not attribute_list:
        return

    estimation_sum = 0.0
    for attribute_name in attribute_list:
        estimation_sum += check_for_estimation_level(estimated_attributes, attribute_name)
    estimation_level = estimation_sum / len(attribute_list)

    if estimation_level < constants.ESTIMATION_LIMIT_HIGH:
        estimated_attributes.append((constants.ENERGY_ATTRIBUTE, estimation_level))


def calculate_one_energy_value(attributes: dict, estimated_attributes: list):
    """Returns the estimated energy based on the given attributes.
       Returns 0.0, if the energy cannot be calculated."""
    active_power = attributes.get("activePower", None)
    if active_power is not None:
        check_if_energy_is_estimate(["activePower"], estimated_attributes)
        return active_power

    illuminance_level = attributes.get("illuminanceLevel", None)
    if illuminance_level is not None:
        estimated_attributes.append((constants.ENERGY_ATTRIBUTE, 0.0))
        return illuminance_level * constants.DEFAULT_VIINIKKA_ENERGY_WITH_FULL_ILLUMINANCE

    intensity = attributes.get("intensity", None)
    voltage = attributes.get("voltage", None)
    if intensity is not None and voltage is not None:
        if isinstance(intensity, (int, float)) and isinstance(voltage, (int, float)):
            # for Viinikka there might be a need for a more complicated formula,
            # since this does not exactly match the activePower values
            # NOTE: Viinikka calculations do not currently actually fall back to here at all.
            check_if_energy_is_estimate(["intensity", "voltage"], estimated_attributes)
            return intensity * voltage

        if isinstance(intensity, dict) and isinstance(voltage, dict):
            if contains_all_phases(intensity) and contains_all_phases(voltage):
                # TODO: find out the proper way to calculate energy from 3-phase values
                # (this might need to be multiplied by sqrt(3))
                # intensity_sum = sum([intensity[phase] for phase in constants.PHASES])
                # voltage_avg = statistics.mean([voltage[phase] for phase in constants.PHASES])
                check_if_energy_is_estimate(
                    [
                        ".".join([attr_name, phase])
                        for phase in constants.PHASES for attr_name in ["intensity", "voltage"]
                    ],
                    estimated_attributes
                )
                return sum([intensity[phase] * voltage[phase] for phase in constants.PHASES])
                # return intensity_sum * voltage_avg

    # cannot calculate energy
    estimated_attributes.append((constants.ENERGY_ATTRIBUTE, 0.0))
    return 0.0


def add_missing_hours(date_string: str, electricity_values: collections.OrderedDict):
    """Fills out the missing hour entries for the given dictionary and returns the result."""
    copied_values = collections.OrderedDict()
    for hour in time_handlers.get_hour_range(date_string):
        time_string = "{:02d}:00:00".format(hour)
        if time_string in electricity_values:
            copied_values[time_string] = electricity_values[time_string]
        else:
            copied_values[time_string] = {}

    return copied_values


def get_value_from_collection(attribute_name: str, value_collection: dict):
    """Returns the attribute value from collection."""
    if "." in attribute_name:
        main_attr, sub_attr = attribute_name.split(".")
        return value_collection.get(main_attr, {}).get(sub_attr, None)
    else:
        return value_collection.get(attribute_name, None)


def add_value_to_collection(value: typing.Union[int, float], attribute_name: str,
                            value_collection: dict, replace=True):
    """Adds the given value to given collection."""
    if "." in attribute_name:
        main_attr, sub_attr = attribute_name.split(".")
        if main_attr not in value_collection:
            value_collection[main_attr] = {}
        if replace or sub_attr not in value_collection[main_attr]:
            value_collection[main_attr][sub_attr] = value
    else:
        if replace or attribute_name not in value_collection:
            value_collection[attribute_name] = value


def check_for_missing_attributes(electricity_values: collections.OrderedDict, attribute_list: list):
    """Returns True only if each entry in the electricity data contains values for all given attributes."""
    for _, attribute_values in electricity_values.items():
        for attribute_name in attribute_list:
            if get_value_from_collection(attribute_name, attribute_values) is None:
                return False

    return True


def add_estimated_attribute(time_string: str, attribute_name: str, estimated_attributes: dict, is_actual=0.0):
    """Adds attribute name to the collection (estimated_attributes) containing information
       about which attribute values have been estimated."""
    if is_actual < constants.ESTIMATION_LIMIT_HIGH:
        if time_string not in estimated_attributes:
            estimated_attributes[time_string] = []
        if attribute_name not in [attr_list[0] for attr_list in estimated_attributes[time_string]]:
            estimated_attributes[time_string].append((attribute_name, is_actual))


def check_for_estimation_level(estimated_attribute_list: list, attribute_name: str):
    """Returns the estimation level for the given attribute. 0 = fully estimated, 1 = no estimation done."""
    for estimated_attribute_name, is_actual in estimated_attribute_list:
        if attribute_name == estimated_attribute_name:
            return is_actual
    return 1.0


def fill_missing_attribute_values(entity: models.Streetlight, date_string: str,
                                  electricity_values: collections.OrderedDict, attribute_list: list):
    """Fills out any missing attribute values for the given data. All attributes are considered separately.
       - Missing values at the beginning are assumed to be the same as the last valid value in the previous day
         between hours 20 and 24. If no valid values are found, the first valid value for the current day is used.
       - Missing values in the middle are filled by using linear fitting.
       - Missing values at the end are assumed to be the same as the last valid values.
       Returns the dictionary containing the information about for which attributes the values were estimated.
    """
    all_time_strings = {}
    missing_attributes = {attribute_name: [] for attribute_name in attribute_list}
    estimated_attributes = {}

    for index, (time_string, attribute_values) in enumerate(electricity_values.items()):
        all_time_strings[index] = time_string
        for attribute_name in attribute_list:
            value = get_value_from_collection(attribute_name, attribute_values)

            if value is None:
                if index == 0:
                    previous_day_starttime = time_handlers.get_previous_day_limit_times(date_string)
                    previous_value = fetch_latest_attribute_value(
                        entity, attribute_name, previous_day_starttime)
                    if previous_value is not None:
                        add_value_to_collection(
                            previous_value,
                            attribute_name,
                            electricity_values[time_string]
                        )
                        add_estimated_attribute(time_string, attribute_name, estimated_attributes, 0.0)
                        continue

                missing_attributes[attribute_name].append(index)

            else:
                for missing_index in missing_attributes[attribute_name]:
                    if missing_index == 0:
                        # if the first value is missing, it is assumed to be the same as the first valid value
                        estimated_value = value
                    else:
                        # using linear fitting for the missing value
                        previous_value = get_value_from_collection(
                            attribute_name,
                            electricity_values[all_time_strings[missing_index-1]])
                        estimated_value = (value - previous_value) / (index - missing_index + 1) + previous_value

                    add_value_to_collection(
                        estimated_value,
                        attribute_name,
                        electricity_values[all_time_strings[missing_index]])
                    add_estimated_attribute(all_time_strings[missing_index], attribute_name, estimated_attributes, 0.0)

                missing_attributes[attribute_name] = []

    for attribute_name in attribute_list:
        for missing_index in missing_attributes[attribute_name]:
            if missing_index > 0:
                # there are missing values at the end of the list => use the latest valid value for them
                add_value_to_collection(
                    get_value_from_collection(
                        attribute_name,
                        electricity_values[all_time_strings[missing_index-1]]),
                    attribute_name,
                    electricity_values[all_time_strings[missing_index]])
                add_estimated_attribute(all_time_strings[missing_index], attribute_name, estimated_attributes, 0.0)

    return estimated_attributes


def fill_missing_phase_values(electricity_values: collections.OrderedDict, attribute_list: list):
    """Fills out the phase values for unknown phases if the values for at least one phase is known.
       Returns the dictionary containing the information about for which attributes the values were estimated."""
    estimated_attributes = {}
    for time_string, attribute_values in electricity_values.items():
        for attribute_name in attribute_list:
            attribute_value = attribute_values.get(attribute_name, {})

            if not contains_all_phases(attribute_value):
                valid_phases = [
                    phase
                    for phase in constants.PHASES
                    if attribute_value.get(phase, None) is not None
                ]

                if valid_phases:
                    avg_value = statistics.mean([attribute_value[phase] for phase in valid_phases])
                    missing_phases = [phase for phase in constants.PHASES if phase not in valid_phases]
                    for phase in missing_phases:
                        full_attribute_name = ".".join([attribute_name, phase])
                        add_value_to_collection(
                            avg_value,
                            full_attribute_name,
                            attribute_values)
                        add_estimated_attribute(time_string, full_attribute_name, estimated_attributes, 0.0)

                elif attribute_name == "voltage":
                    for phase in constants.PHASES:
                        full_attribute_name = ".".join([attribute_name, phase])
                        add_value_to_collection(
                            constants.DEFAULT_TAMPERE_VOLTAGE,
                            full_attribute_name,
                            attribute_values)
                        add_estimated_attribute(time_string, full_attribute_name, estimated_attributes, 0.0)

    return estimated_attributes


def calculate_all_energy_values(electricity_values: collections.OrderedDict, estimated_attributes: dict):
    """Calculates all energy values based on the given electricity data. Returns the calculated energy values."""
    for time_string in electricity_values:
        if time_string not in estimated_attributes:
            estimated_attributes[time_string] = []

    return collections.OrderedDict(
        (time_string, calculate_one_energy_value(attribute_values, estimated_attributes[time_string]))
        for time_string, attribute_values in electricity_values.items()
        if attribute_values.get(constants.ENERGY_ATTRIBUTE, None) is None
    )


def add_energy_to_electricityvalues(energy_attribute: str, electricity_values: collections.OrderedDict,
                                    energy_values: collections.OrderedDict):
    """Adds the calculated energy values to the given electricity data."""
    for time_string, energy_value in energy_values.items():
        add_value_to_collection(
            energy_value,
            energy_attribute,
            electricity_values[time_string])


def combine_estimated_attributes_lists(*estimated_attributes):
    """Combines the given lists for estimated values.
       The parameters are expected to be dictionaries with the keys being time strings and
       the values being a list of the attribute names that have an estimated value."""
    time_strings = []
    for value_dict in estimated_attributes:
        time_strings += list(value_dict.keys())
    time_strings = set(time_strings)

    combined_list = {}
    for time_string in time_strings:
        combined_list[time_string] = []
        for value_dict in estimated_attributes:
            comb_attr_names_only = [comb_attr[0] for comb_attr in combined_list[time_string]]
            for attr_name, estimation_level in value_dict.get(time_string, []):
                if attr_name in comb_attr_names_only:
                    combined_list[time_string][comb_attr_names_only.index(attr_name)] = (
                        attr_name,
                        min(
                            combined_list[time_string][comb_attr_names_only.index(attr_name)][1],
                            estimation_level))
                else:
                    combined_list[time_string].append((attr_name, estimation_level))
        #     combined_list[time_string] += value_dict.get(time_string, [])
        # combined_list[time_string] = list(set(combined_list[time_string]))

    return combined_list


def calculate_energy_values(entity: models.Streetlight, date_string: str,
                            electricity_values: collections.OrderedDict, estimated_values=None):
    """Calculates the used energy values based on the electricity data.
       For the viinikka service, the calculation is based on the activePower attribute or
       in case it is missing on the illuminanceLevel attribute.
       For the tampere service, the calculation is based on the intensity and voltage attributes.
       The calculation tries to fill any gabs in the data by the best estimates."""
    if estimated_values is None:
        estimated_values = {}
    # NOTE: the function works when constants.TIME_INTERVAL_FOR_RECENT_DATA == constants.HOUR_CONSTANT == 3600
    # NOTE: If energy value is already available, it is not calculated again but the attributes will still be filled.
    #       We should only come here if at least some of the energy values are missing.
    electricity_values = add_missing_hours(date_string, electricity_values)
    # NOTE: the following line can be removed if estimated values are also stored in database
    # copied_values = copy.deepcopy(electricity_values)

    service_type = entity.area1.service_type
    if service_type == "viinikka":
        new_estimated_values = fill_missing_attribute_values(
            entity, date_string, electricity_values, [constants.VIINIKKA_PRIMARY_ENERGY_ATTRIBUTE])
        estimated_values = combine_estimated_attributes_lists(estimated_values, new_estimated_values)
        if not check_for_missing_attributes(electricity_values, constants.VIINIKKA_PRIMARY_ENERGY_ATTRIBUTE):
            new_estimated_values = fill_missing_attribute_values(
                entity, date_string, electricity_values, [constants.VIINIKKA_SECONDARY_ENERGY_ATTRIBUTE])
            estimated_values = combine_estimated_attributes_lists(estimated_values, new_estimated_values)

    else:
        new_estimated_values = fill_missing_attribute_values(
            entity, date_string, electricity_values, constants.TAMPERE_ENERGY_ATTRIBUTES_FULL)
        estimated_values = combine_estimated_attributes_lists(estimated_values, new_estimated_values)
        new_estimated_values = fill_missing_phase_values(
            electricity_values, constants.TAMPERE_ENERGY_ATTRIBUTES_MAIN)
        estimated_values = combine_estimated_attributes_lists(estimated_values, new_estimated_values)

    energy_values = calculate_all_energy_values(electricity_values, estimated_values)
    add_energy_to_electricityvalues(
        constants.ATTRIBUTES_DB_FIWARE[service_type][constants.ENERGY_ATTRIBUTE],
        electricity_values,
        energy_values)

    return electricity_values, estimated_values


# def calculate_energy_values2(service_type: str, date_string: str, electricity_values: collections.OrderedDict):
#     """Calculates the used energy values based on the electricity data.
#        For the viinikka service, the calculation is based on the activePower attribute,
#        and for the tampere service, the calculation is based on the intensity and voltage attributes.
#        The calculation tries to fill any gabs in the data by the best estimates."""
#     # NOTE: the function works when constants.TIME_INTERVAL_FOR_RECENT_DATA == constants.HOUR_CONSTANT == 3600

#     copied_values = collections.OrderedDict()
#     for hour in time_handlers.get_hour_range(date_string):
#         time_string = "{:02d}:00:00".format(hour)
#         if time_string in electricity_values:
#             copied_values[time_string] = electricity_values[time_string]
#         else:
#             copied_values[time_string] = {}

#     if service_type == "viinikka":
#         missing_powers = []
#         all_time_strings = {}
#         for index, (time_string, attribute_values) in enumerate(copied_values.items()):
#             all_time_strings[index] = time_string
#             power = attribute_values.get("activePower", None)
#             if power is not None:
#                 copied_values[time_string][constants.ENERGY_ATTRIBUTE] = power

#                 for missing_index in missing_powers:
#                     if missing_index == 0:
#                         # if the first power value is missing it is assumed to be the same as the first valid value
#                         copied_values[all_time_strings[missing_index]][constants.ENERGY_ATTRIBUTE] = power
#                     else:
#                         # using linear fitting for the missing power value
#                         previous_power = copied_values[all_time_strings[missing_index-1]][constants.ENERGY_ATTRIBUTE]
#                         estimated_power = (power - previous_power) / (index - missing_index + 1) + previous_power
#                         copied_values[all_time_strings[missing_index]][constants.ENERGY_ATTRIBUTE] = estimated_power
#                 missing_powers = []

#             else:
#                 missing_powers.append(index)

#         for missing_index in missing_powers:
#             if missing_index == 0:
#                 # In this case there is no valid values at all => use 0 as the energy
#                 # to-do: it seems there are too many zeroes inserted currently => fix this. Might have been solved already. Still implement a search for previous nights values, then try to use the illuminanceLevel for getting the energy.
#                 # - check if there is illuminanceLevel values
#                 #   - if data found, use energy formula: illuminanceLevel * DEFAULT_FULL_ENERGY
#                 #   - if no data, fetch energy data from previous day (fetch full day, consider only 18-24)
#                 #     - if data found, use the last hours value for this missing value
#                 #     - if no data, fetch electricity data from previous day (fetch full day, consider only 18-24)
#                 #       - if data, energy will be calculated => use the last hours energy for this missing value
#                 #     -   if no data, use 0.0 as the default value
#                 copied_values[all_time_strings[missing_index]][constants.ENERGY_ATTRIBUTE] = 0.0
#             else:
#                 # there are missing values at the end of the list => use the latest valid for them
#                 copied_values[all_time_strings[missing_index]][constants.ENERGY_ATTRIBUTE] = \
#                     copied_values[all_time_strings[missing_index - 1]][constants.ENERGY_ATTRIBUTE]

#         return copied_values

#     copied_values_temp = copy.deepcopy(copied_values)
#     all_time_strings = {}
#     missing_attributes = {
#         "intensity": {
#             "L1": [],
#             "L2": [],
#             "L3": []
#         },
#         "voltage": {
#             "L1": [],
#             "L2": [],
#             "L3": []
#         }
#     }
#     attributes = ["intensity", "voltage"]
#     phases = ["L1", "L2", "L3"]
#     for index, (time_string, attribute_values) in enumerate(copied_values_temp.items()):
#         all_time_strings[index] = time_string
#         for attribute_name in attributes:
#             attribute_value = attribute_values.get(attribute_name, {})
#             for phase in phases:
#                 value = attribute_value.get(phase, None)

#                 if value is not None:
#                     for missing_index in missing_attributes[attribute_name][phase]:
#                         if missing_index == 0:
#                             # if the first value is missing it is assumed to be the same as the first valid value
#                             if attribute_name not in copied_values_temp[all_time_strings[missing_index]]:
#                                 copied_values_temp[all_time_strings[missing_index]][attribute_name] = {}
#                             copied_values_temp[all_time_strings[missing_index]][attribute_name][phase] = value
#                         else:
#                             # using linear fitting for the missing value
#                             previous_value = \
#                                 copied_values_temp[all_time_strings[missing_index-1]][attribute_name][phase]
#                             estimated_value = (value - previous_value) / (index - missing_index + 1) + previous_value
#                             if attribute_name not in copied_values_temp[all_time_strings[missing_index]]:
#                                 copied_values_temp[all_time_strings[missing_index]][attribute_name] = {}
#                             copied_values_temp[all_time_strings[missing_index]][attribute_name][phase] = estimated_value
#                     missing_attributes[attribute_name][phase] = []

#                 else:
#                     missing_attributes[attribute_name][phase].append(index)

#     fully_missing_attributes = []
#     for attribute_name in attributes:
#         for phase in phases:
#             for missing_index in missing_attributes[attribute_name][phase]:
#                 if missing_index == 0:
#                     if attribute_name not in copied_values_temp[all_time_strings[missing_index]]:
#                         copied_values_temp[all_time_strings[missing_index]][attribute_name] = {}
#                     copied_values_temp[all_time_strings[missing_index]][attribute_name][phase] = None
#                     copied_values[all_time_strings[missing_index]][constants.ENERGY_ATTRIBUTE] = {"L0": None}
#                 else:
#                     # there are missing values at the end of the list => use the latest valid for them
#                     previous_value = copied_values_temp[all_time_strings[missing_index - 1]][attribute_name][phase]
#                     if attribute_name not in copied_values_temp[all_time_strings[missing_index]]:
#                         copied_values_temp[all_time_strings[missing_index]][attribute_name] = {}
#                     copied_values_temp[all_time_strings[missing_index]][attribute_name][phase] = previous_value
#                     if previous_value is None:

#     for time_string in copied_values_temp:
#         if constants.ENERGY_ATTRIBUTE not in copied_values[time_string]:
#             copied_values[time_string][constants.ENERGY_ATTRIBUTE] = {
#                 "L0": (
#                     sum([copied_values_temp[time_string]["intensity"][phase] for phase in phases]) *
#                     statistics.mean([copied_values_temp[time_string]["voltage"][phase] for phase in phases])
#                 )
#             }

#     return copied_values


def combine_ordered_dicts(first_dict: collections.OrderedDict, second_dict: collections.OrderedDict):
    """Adds the values from the second dictionary to the first dictionary."""
    for time_string, attributes in second_dict.items():
        if time_string not in first_dict:
            first_dict[time_string] = {}

        for attribute_name, attribute_value in attributes.items():
            if isinstance(attribute_value, dict):
                for sub_attr_name, sub_attr_value in attribute_value.items():
                    add_value_to_collection(
                        sub_attr_value,
                        ".".join([attribute_name, sub_attr_name]),
                        first_dict,
                        replace=False)
            else:
                add_value_to_collection(
                    attribute_value,
                    attribute_name,
                    first_dict,
                    replace=False)


def save_request_day_values(entity: models.Streetlight, date_string: str,
                            request_day_values: collections.OrderedDict,
                            old_values=None, estimated_attributes=None):
    """Saves the given request day electricity values to the database."""
    if old_values:
        combine_ordered_dicts(old_values, request_day_values)
        request_day_values = old_values

    request_day_values, estimated_attributes = calculate_energy_values(
        entity, date_string, request_day_values, estimated_attributes)

    check_date = time_handlers.get_dt_object(date_string)
    limit_hour = time_handlers.get_limit_hour(time_handlers.get_time_season(check_date))

    service_type = entity.area1.service_type
    for time_string, attributes in request_day_values.items():
        hour, minute, second = [int(part) for part in time_string.split(":")]
        time_object = check_date.replace(hour=hour, minute=minute, second=second)
        if hour >= limit_hour:
            time_object -= datetime.timedelta(days=1)

        estimated_attributes_for_time = estimated_attributes.get(time_string, {})
        for attribute_name, attribute_value in attributes.items():
            if isinstance(attribute_value, dict):
                for sub_attr_name, sub_attr_value in attribute_value.items():
                    is_actual_check = min(
                        check_for_estimation_level(estimated_attributes_for_time, attribute_name),
                        check_for_estimation_level(
                            estimated_attributes_for_time, ".".join([attribute_name, sub_attr_name]))
                    )
                    measurement = models.Measurement(
                        name=constants.ATTRIBUTES_FIWARE_DB[service_type][attribute_name][sub_attr_name],
                        value_type="realtime",
                        value=sub_attr_value,
                        timestamp=time_object,
                        is_actual=is_actual_check,
                        streetlight_entity=entity)
                    measurement.save()
            else:
                measurement = models.Measurement(
                    name=constants.ATTRIBUTES_FIWARE_DB[service_type][attribute_name],
                    value_type="realtime",
                    value=attribute_value,
                    timestamp=time_object,
                    is_actual=check_for_estimation_level(estimated_attributes_for_time, attribute_name),
                    streetlight_entity=entity)
                measurement.save()

    stored_query = models.MeasurementStored.objects.filter(date=check_date.date(), streetlight_entity=entity)
    if stored_query:
        stored_object = stored_query.first()
    else:
        stored_object = models.MeasurementStored(date=check_date.date(), streetlight_entity=entity)

    time_now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    if (time_now - check_date).total_seconds() > constants.FULL_STORE_LIMIT_SECONDS[service_type]:
        stored_object.realtime_values = "full"
    else:
        stored_object.realtime_values = "part"
    stored_object.save()

    return request_day_values, estimated_attributes


def save_history_values(entity: models.Streetlight, date_string: str, history_values: dict):
    """Saves the given historical electricity values to the database."""
    service_type = entity.area1.service_type
    check_date = time_handlers.get_dt_object(date_string)
    limit_hour = time_handlers.get_limit_hour(time_handlers.get_time_season(check_date))

    for main_fiware_attr, hours in history_values.items():
        for hour, hour_values in hours.items():
            time_object = check_date.replace(hour=hour)
            if hour >= limit_hour:
                time_object -= datetime.timedelta(days=1)

            for aggregation_type in ["avg", "stdev"]:
                aggregation_value = hour_values.get(aggregation_type, None)
                if aggregation_value is None:
                    continue

                if isinstance(aggregation_value, dict):
                    for sub_attr_name, sub_attr_value in aggregation_value.items():
                        measurement = models.Measurement(
                            name=constants.ATTRIBUTES_FIWARE_DB[service_type][main_fiware_attr][sub_attr_name],
                            value_type=aggregation_type,
                            value=sub_attr_value,
                            timestamp=time_object,
                            streetlight_entity=entity)
                        measurement.save()
                else:
                    measurement = models.Measurement(
                        name=constants.ATTRIBUTES_FIWARE_DB[service_type][main_fiware_attr],
                        value_type=aggregation_type,
                        value=aggregation_value,
                        timestamp=time_object,
                        streetlight_entity=entity)
                    measurement.save()

    stored_query = models.MeasurementStored.objects.filter(date=check_date.date(), streetlight_entity=entity)
    if stored_query:
        stored_object = stored_query.first()
    else:
        stored_object = models.MeasurementStored(date=check_date.date(), streetlight_entity=entity)

    stored_object.history_values = "full"
    stored_object.save()


def get_electricity_results_full(entity: models.Streetlight, date_string: str):
    """Loads the electricity data for the given streetlight and date from QuantumLeap.
       Returns the parsed data separated in request day data and history data."""
    service_type = entity.area1.service_type
    entity_id = entity.name
    check_date = time_handlers.get_dt_object(date_string)

    if service_type == "tampere":
        check_result_list = get_data_from_quantumleap(
            service_type=service_type,
            entity_id=entity_id,
            check_date=check_date,
            attributes=constants.ATTRIBUTES.get(service_type, []),
            history_days=constants.HISTORY_DAYS,
            use_aggregation=False,
            time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    else:
        check_result_list = get_data_from_quantumleap(
            service_type=service_type,
            entity_id=entity_id,
            check_date=check_date - datetime.timedelta(days=1),
            attributes=set(constants.ATTRIBUTES.get(service_type, [])).intersection(
                constants.ATTRIBUTES_FOR_HISTORY_COMPARISON),
            history_days=constants.HISTORY_DAYS - 1,
            use_aggregation=True,
            time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)
        check_result_list += get_data_from_quantumleap(
            service_type=service_type,
            entity_id=entity_id,
            check_date=check_date,
            attributes=constants.ATTRIBUTES.get(service_type, []),
            history_days=0,
            use_aggregation=True,
            time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    request_day_data, history_values = handle_streetlight_data(
        streetlight_data_list=check_result_list,
        request_date=check_date,
        time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    request_day_data, estimated_attributes = save_request_day_values(entity, date_string, request_day_data)
    save_history_values(entity, date_string, history_values)
    return request_day_data, history_values, estimated_attributes


def get_electricity_results_history(entity: models.Streetlight, date_string: str):
    """Loads the historical electricity data for the given streetlight and date from QuantumLeap."""
    service_type = entity.area1.service_type
    entity_id = entity.name
    check_date = time_handlers.get_dt_object(date_string)

    check_result_list = get_data_from_quantumleap(
        service_type=service_type,
        entity_id=entity_id,
        check_date=check_date - datetime.timedelta(days=1),
        history_days=constants.HISTORY_DAYS,
        attributes=set(constants.ATTRIBUTES.get(service_type, [])).intersection(
            constants.ATTRIBUTES_FOR_HISTORY_COMPARISON),
        use_aggregation=service_type == "viinikka",
        time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    _, history_values = handle_streetlight_data(
        streetlight_data_list=check_result_list,
        request_date=check_date,
        time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    save_history_values(entity, date_string, history_values)
    return history_values


def get_electricity_results_realtime(entity: models.Streetlight, date_string: str,
                                     existing_values=None, existing_estimated_attributes=None):
    """Loads the request day electricity data for the given streetlight and date from QuantumLeap."""
    service_type = entity.area1.service_type
    entity_id = entity.name
    check_date = time_handlers.get_dt_object(date_string)
    if existing_values:
        strict_start_date = \
            time_handlers.get_dt_object("T".join([date_string, next(reversed(existing_values.keys()))])) + \
            datetime.timedelta(hours=1, seconds=1)
    else:
        strict_start_date = None

    check_result_list = get_data_from_quantumleap(
        service_type=service_type,
        entity_id=entity_id,
        check_date=check_date,
        history_days=0,
        strict_start_date=strict_start_date,
        attributes=constants.ATTRIBUTES.get(service_type, []),
        use_aggregation=service_type == "viinikka",
        time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    request_day_data, _ = handle_streetlight_data(
        streetlight_data_list=check_result_list,
        request_date=check_date,
        time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    request_day_data, estimated_attributes = save_request_day_values(
        entity, date_string, request_day_data,
        existing_values, existing_estimated_attributes
    )
    # if existing_values:
    #     existing_values.update(request_day_data)
    #     if existing_estimated_attributes:
    #         estimated_attributes = combine_estimated_attributes_lists(
    #             existing_estimated_attributes, estimated_attributes)

    #     return existing_values, estimated_attributes

    return request_day_data, estimated_attributes


def parse_single_energy_value(attribute_values):
    """Parses the energy value from the given attributes.
       The attribute_values parameter can be simple numerical value or a dictionary."""
    if isinstance(attribute_values, (int, float)):
        return attribute_values

    if isinstance(attribute_values, dict) and constants.ENERGY_ATTRIBUTE in attribute_values:
        if isinstance(attribute_values[constants.ENERGY_ATTRIBUTE], (int, float)):
            return attribute_values[constants.ENERGY_ATTRIBUTE]
        if (isinstance(attribute_values[constants.ENERGY_ATTRIBUTE], dict) and
                constants.ENERGY_PHASE in attribute_values[constants.ENERGY_ATTRIBUTE]):
            return attribute_values[constants.ENERGY_ATTRIBUTE][constants.ENERGY_PHASE]

    return None


def get_energy_results(entity: models.Streetlight, date_string: str,
                       existing_values=None, existing_estimated_attributes=None):
    """Loads the energy data for the given streetlight and date from QuantumLeap."""
    # the energy values are calculated from the other electricity values that are available in QuantumLeap
    electricity_data, estimated_attributes = get_electricity_results_realtime(
        entity, date_string, existing_values, existing_estimated_attributes)
    if existing_values:
        existing_values.update(electricity_data)
        electricity_data = existing_values

    energy_data = collections.OrderedDict(
        (
            time_string,
            value_holder.ValueHolder(
                parse_single_energy_value(attributes),
                check_for_estimation_level(estimated_attributes.get(time_string, []), constants.ENERGY_ATTRIBUTE))
        )
        for time_string, attributes in electricity_data.items()
        if parse_single_energy_value(attributes) is not None
    )

    return energy_data


def parse_request_day_values(entity_measurements: QuerySet):
    """Parses and returns the request day values from the given QuerySet."""
    realtime_measurements = entity_measurements.filter(
        value_type="realtime", value__isnull=False).order_by("timestamp")

    estimated_attributes = {}

    request_day_values = collections.OrderedDict()
    if realtime_measurements:
        for realtime_measurement in realtime_measurements:
            service_type = realtime_measurement.streetlight_entity.area1.service_type
            time_string = time_handlers.time_str_from_datetime(realtime_measurement.timestamp)
            if time_string not in request_day_values:
                request_day_values[time_string] = {}

            fiware_attribute = constants.ATTRIBUTES_DB_FIWARE[service_type][realtime_measurement.name]
            if "." in fiware_attribute:
                attr, sub_attr = fiware_attribute.split(".")
                if attr not in request_day_values[time_string]:
                    request_day_values[time_string][attr] = {}
                request_day_values[time_string][attr][sub_attr] = realtime_measurement.value
            else:
                request_day_values[time_string][fiware_attribute] = realtime_measurement.value

            if realtime_measurement.is_actual < constants.ESTIMATION_LIMIT_HIGH:
                add_estimated_attribute(
                    time_string, fiware_attribute, estimated_attributes, realtime_measurement.is_actual)

    return request_day_values, estimated_attributes


def parse_history_values(entity_measurements: QuerySet):
    """Parses and returns the history values from the given QuerySet."""
    history_values = {}
    for aggregation_type in ["avg", "stdev"]:
        history_measurements = entity_measurements.filter(value_type=aggregation_type)

        if history_measurements:
            for history_measurement in history_measurements:
                service_type = history_measurement.streetlight_entity.area1.service_type
                fiware_attribute = constants.ATTRIBUTES_DB_FIWARE[service_type][history_measurement.name]
                main_fiware_attr = fiware_attribute.split(".")[0]
                if main_fiware_attr not in history_values:
                    history_values[main_fiware_attr] = {}

                hour = history_measurement.timestamp.hour
                if hour not in history_values[main_fiware_attr]:
                    history_values[main_fiware_attr][hour] = {}
                if aggregation_type not in history_values[main_fiware_attr][hour]:
                    history_values[main_fiware_attr][hour][aggregation_type] = {}

                if "." in fiware_attribute:
                    sub_attr = fiware_attribute.split(".")[-1]
                    history_values[main_fiware_attr][hour][aggregation_type][sub_attr] = history_measurement.value
                else:
                    history_values[main_fiware_attr][hour][aggregation_type] = history_measurement.value

    return history_values


def parse_energy_values(entity_measurements: QuerySet):
    """Parses and returns the energy values from the given QuerySet."""
    energy_measurements = entity_measurements.filter(
        value_type="realtime", value__isnull=False, name=constants.ENERGY_ATTRIBUTE).order_by("timestamp")

    energy_values = collections.OrderedDict()
    if energy_measurements:
        for energy_measurement in energy_measurements:
            time_string = time_handlers.time_str_from_datetime(energy_measurement.timestamp)
            energy_values[time_string] = value_holder.ValueHolder(
                energy_measurement.value, energy_measurement.is_actual)

    return energy_values


def fetch_attribute_values(entity: models.Streetlight, attribute_name: str, start_time: datetime.datetime):
    """Fetches the attribute values for the given entity and attribute and time interval.
       The end time for the time interval will be at the end of the same day. The date should be in the past."""
    # NOTE: this function has copy-pasted parts from several other function => could be done better
    latest_measurement = models.Measurement.objects.filter(
        streetlight_entity=entity,
        name=constants.ATTRIBUTE_COMPACT_DB[attribute_name],
        value_type="realtime",
        value__isnull=False,
        timestamp__gte=start_time,
        timestamp__lt=start_time + datetime.timedelta(hours=constants.PREVIOUS_DAY_CHECK_HOURS)
    ).order_by("-timestamp").first()

    if latest_measurement:
        return latest_measurement.value

    # Since the database did not contain values, load data from QuantumLeap.
    attribute_name_main = attribute_name.split(".")[0]
    check_result_list = get_data_from_quantumleap(
        service_type=entity.area1.service_type,
        entity_id=entity.name,
        check_date=start_time,
        history_days=0,
        strict_start_date=start_time,
        attributes=[attribute_name_main],
        use_aggregation=entity.area1.service_type == "viinikka",
        time_interval_s=constants.TIME_INTERVAL_FOR_RECENT_DATA)

    data_values = ql_data_initial_parsing(check_result_list)

    request_day_data = collections.OrderedDict()
    for time_value, data_value in data_values:
        attribute_value = data_value.get(attribute_name_main, None)
        if attribute_value is None:
            continue
        datetime_value = time_handlers.get_dt_object(time_value)
        time_string_interval = time_handlers.get_time_interval_start(
            str(datetime_value.time()),
            constants.TIME_INTERVAL_FOR_RECENT_DATA,
            time_handlers.get_time_season(datetime_value))

        value_handlers.add_attribute_value(
            request_day_data, time_string_interval, attribute_name_main, attribute_value)

    value_handlers.ql_handle_request_day_data(request_day_data)

    wanted_attribute_values = collections.OrderedDict()
    for time_string, data_value in request_day_data.items():
        attribute_value = data_value.get(attribute_name_main, None)
        if attribute_value is None:
            continue

        # NOTE: this assumes that the local time is never before UTC time
        hour, minute, second = [int(part) for part in time_string.split(":")]
        time_object = start_time.replace(hour=hour, minute=minute, second=second)

        if isinstance(attribute_value, dict):
            for sub_attr_name, sub_attr_value in attribute_value.items():
                if ".".join([attribute_name_main, sub_attr_name]) == attribute_name:
                    wanted_attribute_values[time_string] = sub_attr_value

                measurement = models.Measurement(
                    name=constants.ATTRIBUTES_FIWARE_DB[entity.area1.service_type][attribute_name_main][sub_attr_name],
                    value_type="realtime",
                    value=sub_attr_value,
                    timestamp=time_object,
                    streetlight_entity=entity)
                measurement.save()
        else:
            wanted_attribute_values[time_string] = attribute_value

            measurement = models.Measurement(
                name=constants.ATTRIBUTES_FIWARE_DB[entity.area1.service_type][attribute_name_main],
                value_type="realtime",
                value=attribute_value,
                timestamp=time_object,
                streetlight_entity=entity)
            measurement.save()

    return wanted_attribute_values


def fetch_latest_attribute_value(entity: models.Streetlight, attribute_name: str, start_time: datetime.datetime):
    """Fetches the latest attribute value for the given entity and attribute and time interval.
       The end time for the time interval will be at the end of the same day. The date should be in the past."""
    values = fetch_attribute_values(entity, attribute_name, start_time)

    if values is None:
        return None

    if isinstance(values, (int, float)):
        return values

    for _, value in reversed(values.items()):
        if value is not None:
            return value

    return None


def parse_estimated_attributes(electricity_data: dict):
    """Takes in a dictionary containing time strings as keys and with the values being dictionaries
       of attribute values that are given as ValueHolder objects.
       Returns a dictionary containing the lists of estimated attributes for each time string.
       The determination is done by checking the is_actual properties of the ValueHolder objects.
    """
    estimated_attributes = {}
    for time_string, attribute_dictionary in electricity_data.items():
        if isinstance(attribute_dictionary, value_holder.ValueHolder):
            # if we get a value instead of a dictionary, we are dealing with energy values
            if attribute_dictionary.is_actual < constants.ESTIMATION_LIMIT_HIGH:
                add_estimated_attribute(
                    time_string, constants.ENERGY_ATTRIBUTE, estimated_attributes, attribute_dictionary.is_actual)
        else:
            for attribute_name, attribute_value in attribute_dictionary.items():
                if attribute_value.is_actual < constants.ESTIMATION_LIMIT_HIGH:
                    add_estimated_attribute(
                        time_string, attribute_name, estimated_attributes, attribute_value.is_actual)

    return estimated_attributes


def from_value_holder_to_value(attribute_data):
    """Takes in a dictionary containing ValueHolder objects as values and
       returns a similar dictionary but containing only the actual values."""
    if isinstance(attribute_data, value_holder.ValueHolder):
        # if we get just one value, we are dealing with energy value
        return {
            constants.ENERGY_ATTRIBUTE: attribute_data.value
        }

    return {
        attribute_name: attribute_value.value
        for attribute_name, attribute_value in attribute_data.items()
    }


def from_value_holder_collection_to_value_collection(electricity_data):
    """Takes in a dictionary containing time strings as keys and with the values being dictionaries
       of attribute values that are given as ValueHolder objects.
       Returns a similar dictionary but with the attribute value objects replaced by the actual values.
    """
    if isinstance(electricity_data, collections.OrderedDict):
        return collections.OrderedDict(
            (time_string, from_value_holder_to_value(attribute_data))
            for time_string, attribute_data in electricity_data.items()
        )

    # assume electricity data is of type dict
    return {
        time_string: from_value_holder_to_value(attribute_data)
        for time_string, attribute_data in electricity_data.items()
    }


def fetch_electricity_values(entity: models.Streetlight, date_string: str):
    """Loads the electricity for the given entity and date. Uses the internal database as the primary source and
       loads the data from QuantumLeap when necessary. Stores all the loaded data to the internal database."""
    time_limit_low, time_limit_high = time_handlers.get_limit_times(date_string)

    date_object = time_handlers.get_dt_object(date_string)
    check_storage = models.MeasurementStored.objects.filter(streetlight_entity=entity, date=date_object)
    if check_storage:
        storage_object = check_storage.first()
        request_day_storage = storage_object.realtime_values
        history_storage = storage_object.history_values

        entity_measurements = models.Measurement.objects.filter(
            streetlight_entity=entity, value__isnull=False,
            timestamp__gte=time_limit_low, timestamp__lt=time_limit_high)

        if request_day_storage == "none" and history_storage == "none":
            request_day_values, history_values, estimated_attributes = \
                get_electricity_results_full(entity=entity, date_string=date_string)
        else:
            if history_storage == "full":
                history_values = parse_history_values(entity_measurements)
            else:
                history_values = get_electricity_results_history(entity=entity, date_string=date_string)

            if request_day_storage == "full":
                request_day_values, estimated_attributes = parse_request_day_values(entity_measurements)
            elif request_day_storage == "part":
                old_request_day_value_objects, old_estimated_attributes = parse_request_day_values(entity_measurements)
                request_day_values, estimated_attributes = get_electricity_results_realtime(
                    entity=entity, date_string=date_string,
                    existing_values=old_request_day_value_objects,
                    existing_estimated_attributes=old_estimated_attributes)
            else:
                request_day_values, estimated_attributes = get_electricity_results_realtime(
                    entity=entity, date_string=date_string)

    else:
        request_day_values, history_values, estimated_attributes = \
            get_electricity_results_full(entity=entity, date_string=date_string)

    value_handlers.combine_with_history(entity.area1.service_type, request_day_values, history_values)
    return request_day_values, estimated_attributes


def create_common_info(attribute_infos: dict, switch_off_check: int, switch_on_check: int):
    """Creates and returns the general information logs from the given attribute information."""
    attr_info_list = [
        attribute_infos[name]["info_level"]
        for name in attribute_infos
        if attribute_infos[name]["info_level"] != ""
    ]
    if attr_info_list:
        info_level = value_handlers.get_highest_info_level(attr_info_list)
    else:
        info_level = constants.INFO_LEVEL_INT2STR[1]

    light_info = "/".join({
        attribute_infos[name]["light_info"]
        for name in attribute_infos
        if attribute_infos[name]["light_info"] != "unknown" and attribute_infos[name]["light_info"] != ""
    })

    if switch_off_check < 0 or switch_on_check > 0:
        expected_light_info = "on"
    elif switch_off_check > 0 and switch_on_check < 0:
        expected_light_info = "off"
    else:
        expected_light_info = "unknown"

    time_info_list = []
    if (info_level != "Ok" and
            ((expected_light_info == "on" and light_info == "off") or
             (expected_light_info == "off" and light_info == "on"))):
        time_info = time_handlers.get_time_info(switch_off_check, switch_on_check)[1]
        if time_info != "":
            time_info_list = [time_info]

    problem_info = "\n".join(time_info_list + [
        " ".join([attribute_infos[name]["problem_info"], constants.SHORT_ATTRIBUTE_NAMES[name]])
        for name in attribute_infos if attribute_infos[name]["problem_info"] != ""
    ])

    extra_info = "\n".join([
        ": ".join([constants.SHORT_ATTRIBUTE_NAMES[name], attribute_infos[name]["extra_info"]])
        for name in attribute_infos if attribute_infos[name]["extra_info"] != ""
    ])

    return {
        "log_level": info_level,
        "light_info": light_info,
        "problem_info": problem_info,
        "extra_info": extra_info,
        "values": {}
    }


def create_attribute_info(service_type: str, electricity_values: dict, switch_off_check: int, switch_on_check: int):
    """Analyses the given electricity values and returns the information from the analysis."""
    attribute_infos = {}
    for attribute_name, attribute_value in electricity_values.items():
        if attribute_name not in constants.ATTRIBUTES.get(service_type, []):
            continue
        attr_info_level, attr_light_info, attr_extra_info = attribute_value_check(
            service_type=service_type,
            switch_checks=(switch_off_check, switch_on_check),
            attribute_name=attribute_name,
            attribute_value=attribute_value)

        if attr_info_level in ("Warning", "Error"):
            attr_problem_info = "unusual"
        else:
            attr_problem_info = ""

        attribute_infos[attribute_name] = {
            "value": attribute_value.get("value", None),
            "info_level": attr_info_level,
            "light_info": attr_light_info,
            "problem_info": attr_problem_info,
            "extra_info": attr_extra_info
        }

    return create_common_info(attribute_infos, switch_off_check, switch_on_check), attribute_infos


def create_electricity_log_text(service_type: str, entity_name: str, time_string: str,
                                electricity_values: dict, switch_times: list, date_string: str,
                                estimated_attributes: dict):
    """Determines and returns the log text corresponding to the given entity, date, electricity values and
       expected switch off and switch on times."""
    time_season = time_handlers.get_time_season(time_handlers.get_dt_object(date_string))
    time_seconds_start = time_handlers.seconds_from_time(time_string, time_season)
    time_seconds_end = time_seconds_start + constants.TIME_INTERVAL_FOR_RECENT_DATA
    switch_off_check = value_handlers.distance_from_interval(
        time_seconds_start, time_seconds_end,
        *[time_handlers.seconds_from_time(x, time_season) for x in switch_times[0][:]])
    switch_on_check = value_handlers.distance_from_interval(
        time_seconds_start, time_seconds_end,
        *[time_handlers.seconds_from_time(x, time_season) for x in switch_times[1][:]])

    log_info, attribute_infos = \
        create_attribute_info(service_type, electricity_values, switch_off_check, switch_on_check)

    log_info["entity_id"] = entity_name
    log_info["time"] = time_string

    for attribute_name in constants.ATTRIBUTES.get(service_type, []):
        value = attribute_infos.get(attribute_name, {}).get("value", "")
        if value is None:
            value = ""

        if service_type == "tampere":
            for phase in constants.PHASES:
                if isinstance(value, dict):
                    phase_value = value.get(phase, "")
                else:
                    phase_value = ""
                display_name = constants.SHORT_ATTRIBUTE_NAMES_WITH_PHASE[(attribute_name, phase)]
                combined_name = ".".join([attribute_name, phase])
                log_info["values"][display_name] = value_holder.ValueHolder(
                    phase_value,
                    check_for_estimation_level(estimated_attributes.get(time_string, []), combined_name)
                )
        else:
            display_name = constants.SHORT_ATTRIBUTE_NAMES[attribute_name]
            log_info["values"][display_name] = value_holder.ValueHolder(
                value,
                check_for_estimation_level(estimated_attributes.get(time_string, []), attribute_name)
            )

    return log_info


# def fetch_electricity_results(entity: models.Streetlight, date_string: str, switch_times: list):
#     """Loads the electricity data analysis for the given entity and date. Uses the given expected switch off and
#        switch on times to determine light switch related warnings.
#        Returns a tuple: (request_day_values, estimated_attributes)
#     """
#     request_day_values, estimated_attributes = fetch_electricity_values(entity, date_string)
#     service_type = entity.area1.service_type
#     entity_name = entity.name.split(":")[-1]
#     return [
#         create_electricity_log_text(
#             service_type,
#             entity_name,
#             time_string,
#             electricity_values,
#             switch_times,
#             date_string,
#             estimated_attributes
#         )
#         for time_string, electricity_values in request_day_values.items()]


def get_real_switch_times_only(service_type: str, entity_id: str, date_string: str):
    """Loads electricity data for the given entity and given date from QuantumLeap.
       Calculates and returns the actual switch off and switch on times."""
    check_date = time_handlers.get_dt_object(date_string)

    check_result_list = get_data_from_quantumleap(
        service_type=service_type,
        entity_id=entity_id,
        check_date=check_date,
        history_days=0,
        attributes=constants.ATTRIBUTES_FOR_SWITCH_TIME.get(service_type, []),
        use_aggregation=service_type == "viinikka",
        time_interval_s=constants.TIME_INTERVAL_FOR_SWITCH_TIME
    )

    request_day_values, history_values = handle_streetlight_data(
        streetlight_data_list=check_result_list,
        request_date=check_date,
        time_interval_s=constants.TIME_INTERVAL_FOR_SWITCH_TIME)
    value_handlers.combine_with_history(
        service_type=service_type,
        request_day_values=request_day_values,
        history_values=history_values)

    return time_handlers.get_real_switch_times(request_day_values, date_string)


def get_type_real_switch_times_only(service_type: str, entity_type: str, date_string: str, entity_ids: list):
    """Loads the electricity data for all streetlights of the given type for the given day.
       Calculates the actual switch off and switch on times based on the loaded electricity data.
       Returns the actual switch off and switch on times."""
    check_date = time_handlers.get_dt_object(date_string)

    check_result = get_type_data_from_quantumleap(
        service_type=service_type,
        entity_type=entity_type,
        check_date=check_date,
        history_days=0,
        attributes=constants.ATTRIBUTES_FOR_SWITCH_TIME.get(service_type, []),
        use_aggregation=service_type == "viinikka",
        time_interval_s=constants.TIME_INTERVAL_FOR_SWITCH_TIME,
        entity_ids=entity_ids)

    request_day_data, history_values = handle_type_streetlight_data(
        streetlight_data=check_result,
        request_date=check_date,
        time_interval_s=constants.TIME_INTERVAL_FOR_SWITCH_TIME)
    combine_type_with_history(
        service_type=service_type,
        request_day_values=request_day_data,
        history_values=history_values)

    return {
        entity_id: time_handlers.get_real_switch_times(entity_data, date_string)
        for entity_id, entity_data in request_day_data.items()
    }


def get_switch_results_only(entity_id, real_switch_times, switch_times):
    """Compares the actual and expected switch off and switch on times and
       returns the detailed analysis results as a dictionary."""
    off_interval_len = time_handlers.get_interval_len(*real_switch_times[0])
    on_interval_len = time_handlers.get_interval_len(*real_switch_times[1])
    switch_off_int = time_handlers.distance_from_interval_str(*real_switch_times[0], *switch_times[0])
    switch_on_int = time_handlers.distance_from_interval_str(*real_switch_times[1], *switch_times[1])

    for time_list in real_switch_times:
        time_list[:] = [constants.MISSING_TIME if time_string is None or time_string == "None"
                        else time_string
                        for time_string in time_list]

    info = {
        "log_level": "Ok",
        "entity_id": entity_id.split(":")[-1],
        "switch_off": constants.TIME_INTERVAL_SEPARATOR.join(real_switch_times[0]),
        "switch_on": constants.TIME_INTERVAL_SEPARATOR.join(real_switch_times[1]),
        "inacc_off": "",
        "inacc_on": "",
        "off_too_early": "",
        "off_too_late": "",
        "on_too_early": "",
        "on_too_late": ""
    }

    problem_count = 0
    wrong_switch_off_time = False
    wrong_switch_on_time = False
    if off_interval_len < 0 and on_interval_len < 0:
        info["inacc_off"] = "X"
        info["inacc_on"] = "X"
        problem_count += 2
        wrong_switch_off_time = True
        wrong_switch_on_time = True
    elif off_interval_len < 0:
        info["inacc_off"] = "X"
        problem_count += 1
        wrong_switch_off_time = True
    elif on_interval_len < 0:
        info["inacc_on"] = "X"
        problem_count += 1
        wrong_switch_on_time = True

    if (off_interval_len > constants.TIME_INTERVAL_WARNING_LIMIT and
            on_interval_len > constants.TIME_INTERVAL_WARNING_LIMIT):
        info["inacc_off"] = "X"
        info["inacc_on"] = "X"
        problem_count += 2
        wrong_switch_off_time = True
        wrong_switch_on_time = True
    elif off_interval_len > constants.TIME_INTERVAL_WARNING_LIMIT:
        info["inacc_off"] = "X"
        problem_count += 1
        wrong_switch_off_time = True
    elif on_interval_len > constants.TIME_INTERVAL_WARNING_LIMIT:
        info["inacc_on"] = "X"
        problem_count += 1
        wrong_switch_on_time = True

    if switch_off_int < -constants.OK_LIMIT_TIME:
        info["off_too_early"] = time_handlers.timestring_from_int(
            -switch_off_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)
        problem_count += 1
        wrong_switch_off_time = True
    elif switch_off_int > constants.OK_LIMIT_TIME:
        info["off_too_late"] = time_handlers.timestring_from_int(
            switch_off_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)
        problem_count += 1
        wrong_switch_off_time = True

    if switch_on_int < -constants.OK_LIMIT_TIME:
        info["on_too_early"] = time_handlers.timestring_from_int(
            -switch_on_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)
        problem_count += 1
        wrong_switch_on_time = True
    elif switch_on_int > constants.OK_LIMIT_TIME:
        info["on_too_late"] = time_handlers.timestring_from_int(
            switch_on_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)
        problem_count += 1
        wrong_switch_on_time = True

    if problem_count > 0:
        info["log_level"] = "Warning"

    info["db_warnings"] = {
        "wrong_switch_off_time": wrong_switch_off_time,
        "wrong_switch_on_time": wrong_switch_on_time
    }

    return info


def get_switch_results_only_simple(real_switch_times, expected_switch_times):
    """Compares the actual and expected switch off and switch on times and
       returns the simple analysis results as a dictionary."""
    off_interval_len = time_handlers.get_interval_len(*real_switch_times[0])
    on_interval_len = time_handlers.get_interval_len(*real_switch_times[1])
    switch_off_int = time_handlers.distance_from_interval_str(*real_switch_times[0], *expected_switch_times[0])
    switch_on_int = time_handlers.distance_from_interval_str(*real_switch_times[1], *expected_switch_times[1])

    for time_list in real_switch_times:
        time_list[:] = [constants.MISSING_TIME if time_string is None or time_string == "None"
                        else time_string
                        for time_string in time_list]

    problem_count = 0
    switch_off_info = []
    switch_on_info = []
    wrong_switch_off_time = False
    wrong_switch_on_time = False

    if off_interval_len < 0 or off_interval_len > constants.TIME_INTERVAL_WARNING_LIMIT:
        switch_off_info.append("inaccurate")
        problem_count += 1
        wrong_switch_off_time = True
    if on_interval_len < 0 or on_interval_len > constants.TIME_INTERVAL_WARNING_LIMIT:
        switch_on_info.append("inaccurate")
        problem_count += 1
        wrong_switch_on_time = True

    if switch_off_int < -constants.OK_LIMIT_TIME:
        switch_off_info.append(" ".join([
            "early",
            time_handlers.timestring_from_int(-switch_off_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)]))
        problem_count += 1
        wrong_switch_off_time = True
    elif switch_off_int > constants.OK_LIMIT_TIME:
        switch_off_info.append(" ".join([
            "late",
            time_handlers.timestring_from_int(switch_off_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)]))
        problem_count += 1
        wrong_switch_off_time = True

    if switch_on_int < -constants.OK_LIMIT_TIME:
        switch_on_info.append(" ".join([
            "early",
            time_handlers.timestring_from_int(-switch_on_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)]))
        problem_count += 1
        wrong_switch_on_time = True
    elif switch_on_int > constants.OK_LIMIT_TIME:
        switch_on_info.append(" ".join([
            "late",
            time_handlers.timestring_from_int(switch_on_int, constants.INCLUDE_SECONDS_IN_TIMESTAMPS)]))
        problem_count += 1
        wrong_switch_on_time = True

    if problem_count > 0:
        log_level = "Warning"
    else:
        log_level = "Ok"

    return {
        "log_level": log_level,
        "switch_off": constants.TIME_INTERVAL_SEPARATOR.join(real_switch_times[0]),
        "switch_on": constants.TIME_INTERVAL_SEPARATOR.join(real_switch_times[1]),
        "switch_off_info": ", ".join(switch_off_info),
        "switch_on_info": ", ".join(switch_on_info),
        "db_warnings": {
            "wrong_switch_off_time": wrong_switch_off_time,
            "wrong_switch_on_time": wrong_switch_on_time
        }
    }


def fetch_switch_time_results(entity: models.Streetlight, date_string: str, switch_times: list, simple=False):
    """Returns the light switch time analysis based on the illuminance and electricity data."""
    date_object = time_handlers.get_dt_object(date_string).date()
    stored_times = models.SwitchTime.objects.filter(streetlight=entity, date=date_object)
    stored_time_off = stored_times.filter(switch_type="off")
    stored_time_on = stored_times.filter(switch_type="on")

    if stored_time_off and stored_time_on:
        switch_off_object = stored_time_off.first()
        switch_on_object = stored_time_on.first()
        real_switch_times = (
            [
                time_handlers.str_from_time(switch_off_object.low_value),
                time_handlers.str_from_time(switch_off_object.high_value)],
            [
                time_handlers.str_from_time(switch_on_object.low_value),
                time_handlers.str_from_time(switch_on_object.high_value)])

    else:
        real_switch_times = get_real_switch_times_only(
            service_type=entity.area1.service_type,
            entity_id=entity.name,
            date_string=date_string)

        for real_switch_time, switch_type in zip(real_switch_times, ["off", "on"]):
            time_handlers.store_switch_time(entity, real_switch_time, date_object, switch_type, "streetlight")

    if simple:
        return get_switch_results_only_simple(real_switch_times, switch_times)
    return get_switch_results_only(entity.name, real_switch_times, switch_times)


def fetch_all_switch_time_results(entities: QuerySet, date_string: str, switch_times: list,
                                  area_name=None, simple=False):
    """Returns the light switch time analysis based on the illuminance and electricity data for all given entities."""
    if not entities:
        return []
    if len(entities) == 1:
        entity = entities.first()
        switch_info = fetch_switch_time_results(entity, date_string, switch_times, simple)
        # save_db_warnings(entity, date_string, switch_info.get("db_warnings", {}))
        return [{
            "id": entity.id,
            "full_name": entity.name,
            "name": entity.name.split(":")[-1],
            "info": switch_info
            }]

    first_entity = entities.first()
    date_object = time_handlers.date_from_str(date_string)
    stored_times = models.SwitchTime.objects.filter(streetlight=first_entity, date=date_object)
    stored_time_off = stored_times.filter(switch_type="off")
    stored_time_on = stored_times.filter(switch_type="on")

    if stored_time_off and stored_time_on:
        # since the first entity has stored times, assume that most of them has
        # and go through them one by one
        results = []
        for entity in entities:
            switch_info = fetch_switch_time_results(entity, date_string, switch_times, simple)
            # save_db_warnings(entity, date_string, switch_info.get("db_warnings", {}))
            results.append({
                "id": entity.id,
                "full_name": entity.name,
                "name": entity.name.split(":")[-1],
                "info": switch_info
            })
        return results

    # since the first entity does not have stored times, assume that most of them does not either
    # and fetch the data for all entities of the same type
    real_switch_times = get_type_real_switch_times_only(
        service_type=first_entity.area1.service_type,
        entity_type=first_entity.group_type,
        date_string=date_string,
        entity_ids=[entity_query_object.name for entity_query_object in entities])
    for entity in entities:
        if entity.name not in real_switch_times:
            real_switch_times[entity.name] = [[constants.MISSING_TIME] * 2] * 2

    results = []
    for entity_name, entity_real_switch_times in real_switch_times.items():
        entity_object = utils.get_streetlight_without_area(entity_name, identifier_name="name")
        if entity_object is None:
            continue
        for entity_real_switch_time, switch_type in zip(entity_real_switch_times, ["off", "on"]):
            time_handlers.store_switch_time(
                entity_object, entity_real_switch_time, date_object, switch_type, "streetlight")

        if area_name:
            entity_object, _ = utils.get_streetlight(area_name, entity_name, identifier_name="name", update=False)
            if entity_object is None or entity_object not in entities:
                continue

        if simple:
            switch_results = get_switch_results_only_simple(entity_real_switch_times, switch_times)
        else:
            switch_results = get_switch_results_only(
                entity_object.name, entity_real_switch_times, switch_times)

        results.append({
            "id": entity_object.id,
            "full_name": entity_object.name,
            "name": entity_object.name.split(":")[-1],
            "info": switch_results
        })

    return results


def save_db_warnings(streetlight_object, date_string: str, db_warnings: dict):
    """Saves the given warnings to the database."""
    date_object = time_handlers.get_dt_object(date_string).date()
    old_warnings = models.DateWarning.objects.filter(streetlight_entity=streetlight_object, date=date_object)
    if old_warnings:
        new_warnings = old_warnings.first()

    else:
        new_warnings = models.DateWarning(
            streetlight_entity=streetlight_object,
            date=date_object
        )

    warning_list = [
        "not_connected",
        "missing_data_one",
        "missing_data_half",
        "wrong_switch_off_time",
        "wrong_switch_on_time"
    ]
    for warning in warning_list:
        if warning in db_warnings:
            setattr(new_warnings, warning, db_warnings[warning])
    new_warnings.save()
