# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module for handling various calculations and comparisons with different values."""

import collections
import statistics

import streetlight.helpers.constants as constants


def compare2(value1, value2, compare_function):
    """Compares two values with the given comparison function.

    :param value1: the first value for the comparison
    :param value2: the second value for the comparison
    :param compare_function: the comparison function e.g. max or min
    :returns: Result of the comparison. If one of the values is None, returns the other value.
    """
    if value1 is None:
        return value2
    if value2 is None:
        return value1
    return compare_function(value1, value2)


def compare(value_list: list, compare_function):
    """Returns the result of the given compare_function used on the value_list.
       If the given list is empty, returns None."""
    if value_list:
        return compare_function(value_list)
    return None


def distance_from_interval(value_start: int, value_end: int, interval_start: int, interval_end: int):
    """Returns the shortest distance from [value_start, value_end] to [interval_start, interval_end].
       If the value interval is on the left side, the distance is given as a negative number.
       If the value interval is on the right side, the distance is given as a positive number.
       If the two intervals touch, the returned distance is 0.
    """
    # if necessary adjust the start values by 86400 (seconds in a day) to ensure that start <= end
    while value_start is not None and value_end is not None and value_start > value_end:
        value_start -= constants.DAY_CONSTANT
    while interval_start is not None and interval_end is not None and interval_start > interval_end:
        interval_start -= constants.DAY_CONSTANT

    if value_start is None and value_end is None:
        return 0

    if value_start is None:
        if interval_start is None or interval_start <= value_end:
            return 0
        return -(interval_start - value_end)

    if value_end is None:
        if interval_end is None or interval_end >= value_start:
            return 0
        return value_start - interval_end

    if interval_start is None:
        if interval_end is None or value_start <= interval_end:
            return 0
        return value_start - interval_end

    if interval_end is None:
        if value_end >= interval_start:
            return 0
        return -(interval_start - value_end)

    if value_end < interval_start:
        return -(interval_start - value_end)

    if value_start > interval_end:
        return value_start - interval_end

    return 0


def get_highest_info_level(info_level_set: set):
    """Return the highest info level in the given set."""
    if not info_level_set:
        return None
    if isinstance(info_level_set, set):
        return constants.INFO_LEVEL_INT2STR[1]
    return constants.INFO_LEVEL_INT2STR[
        max([constants.INFO_LEVEL_STR2INT[info_level] for info_level in info_level_set])]


def get_light_status(attribute_value: dict):
    """Return the streetlight status ("on", "off", "unknown") depending of the given attribute."""
    value = attribute_value.get("value", None)
    if value is None:
        return "unknown"

    limit = attribute_value.get("limit", None)

    if isinstance(value, str):
        if limit is not None and value == limit:
            return "on"
        return "off"

    if isinstance(value, dict):
        if not isinstance(limit, dict):
            return "unknown"
        value_found = False
        for part_name, part_value in value.items():
            if part_value is None:
                continue
            part_limit = limit.get(part_name, None)
            if part_limit is not None:
                if part_value >= part_limit:
                    return "on"
                value_found = part_value >= 0

        if value_found:
            return "off"
        return "unknown"

    if value < 0:
        return "unknown"
    if limit is not None and value >= limit:
        return "on"
    return "off"


def adjust_value(value, limit_min, limit_max):
    """Returns the adjusted value given the interval [limit_min, limit_max]."""
    if value < limit_min:
        return limit_min
    if value > limit_max:
        return limit_max
    return value


def get_statistics(value_list: list):
    """Calculates and returns average and standard deviation values for the given list."""
    count = len(value_list)
    if not value_list:
        return {"count": count}
    first_value = value_list[0]

    if isinstance(first_value, (int, float)):
        stats = {
            "count": count,
            "avg": round(statistics.mean(value_list), 3)
        }
        if count > 1:
            stats["stdev"] = round(statistics.stdev(value_list), 3)

    elif isinstance(first_value, dict):
        stats = {}
        for part_name in first_value:
            part_list = [
                value[part_name]
                for value in value_list if value[part_name] is not None]
            part_stats = get_statistics(part_list)
            if part_stats:
                for stat_name, stat_value in part_stats.items():
                    if stat_name not in stats:
                        stats[stat_name] = {}
                    stats[stat_name][part_name] = stat_value

    return stats


def get_mean_value(value_list: list):
    """Returns the mean value of the list."""
    if value_list:
        first_value = value_list[0]

        if isinstance(first_value, (float, int)):
            return round(statistics.mean(value_list), 3)

        if isinstance(first_value, str):
            return first_value

        if isinstance(first_value, dict):
            mean_dict = {}
            for part_name in first_value:
                part_list = [
                    value[part_name]
                    for value in value_list if value[part_name] is not None]
                part_mean = get_mean_value(part_list)
                if part_mean is not None:
                    mean_dict[part_name] = part_mean
            if mean_dict:
                return mean_dict

    return None


def value_within_limits(attribute_value: dict):
    """Returns True, if the attribute value is within normal limits."""
    value = attribute_value.get("value", None)
    avg = attribute_value.get("history", {}).get("avg", None)
    stdev = attribute_value.get("history", {}).get("stdev", None)

    if value is None or avg is None or stdev is None:
        return True
    if isinstance(value, dict):
        for part_name, part_value in value.items():
            part_avg = avg.get(part_name, None)
            part_stdev = stdev.get(part_name, None)
            if part_value is not None and part_avg is not None and part_stdev is not None:
                part_stdev = max(part_stdev, constants.MIN_STDEV)
                if abs(part_value - part_avg) > constants.STDS_FROM_AVERAGE * part_stdev:
                    return False
        return True

    stdev = max(stdev, constants.MIN_STDEV)
    return abs(value - avg) <= constants.STDS_FROM_AVERAGE * stdev


def value_outside_limits(attribute_name: str, attribute_value):
    """Returns whether the given attribute value is too large for normal operation."""
    if isinstance(attribute_value, dict):
        if "value" in attribute_value:
            attribute_value = attribute_value["value"]
        if isinstance(attribute_value, dict):
            for phase in constants.PHASES:
                full_attribute_name = ".".join([attribute_name, phase])
                if (full_attribute_name in attribute_value and
                        value_outside_limits(full_attribute_name, attribute_value[full_attribute_name])):
                    return True
            return False

    return (attribute_value is None or
            attribute_value < constants.ATTRIBUTE_VALUE_LIMITS[attribute_name]["low"] or
            attribute_value > constants.ATTRIBUTE_VALUE_LIMITS[attribute_name]["high"])


def get_max_avg(history_values: dict):
    """Returns the maximum average value from the historical data."""
    if not history_values:
        return None
    avg_list = [hour_value["avg"] for hour, hour_value in history_values.items() if "avg" in hour_value]
    if not avg_list:
        return None

    first_item = avg_list[0]
    if isinstance(first_item, dict):
        max_avg_dict = {}
        for part_name in first_item:
            part_list = [part_value[part_name] for part_value in avg_list if part_name in part_value]
            if part_list:
                max_avg_dict[part_name] = max(part_list)
        return max_avg_dict

    return max(avg_list)


def get_intensity_limit_value(service_type: str, max_avg):
    """Returns the intensity limit value that indicates that the streetlight is on."""
    if service_type == "tampere":
        limit = {}
        if not max_avg:
            for phase in constants.PHASES:
                limit[phase] = constants.LIMIT_CURRENT_3PHASE_MIN
        else:
            for phase in constants.PHASES:
                if phase not in max_avg:
                    limit[phase] = constants.LIMIT_CURRENT_3PHASE_MIN
                else:
                    limit[phase] = adjust_value(
                        round(max_avg[phase] / 5, 3),
                        constants.LIMIT_CURRENT_3PHASE_MIN,
                        constants.LIMIT_CURRENT_3PHASE_MAX)
        return limit

    if not max_avg:
        return constants.LIMIT_CURRENT_1PHASE_MIN
    return adjust_value(
        round(max_avg / 3, 3),
        constants.LIMIT_CURRENT_1PHASE_MIN,
        constants.LIMIT_CURRENT_1PHASE_MAX)


def get_activepower_limit_value(max_avg):
    """Returns the active power limit value that indicates that the streetlight is on."""
    if not max_avg:
        return constants.LIMIT_VOLTAGE_MIN
    return adjust_value(round(max_avg / 3, 3), constants.LIMIT_POWER_MIN, constants.LIMIT_POWER_MAX)


def get_voltage_limit_value(service_type: str, max_avg):
    """Returns the voltage limit value that indicates that the streetlight is on."""
    if service_type == "tampere":
        # the 3-phase voltage values are the same whether lights are on or off >= no limit values
        limit = {}
        for phase in constants.PHASES:
            limit[phase] = None
        return limit

    if not max_avg:
        return constants.LIMIT_VOLTAGE_MIN
    return adjust_value(
        round(max_avg / 5, 3),
        constants.LIMIT_VOLTAGE_MIN,
        constants.LIMIT_VOLTAGE_MAX)


def get_illuminancelevel_limit_value(max_avg):
    """Returns the illuminance level value that indicates that the streetlight is on."""
    if not max_avg:
        return constants.LIMIT_ILLUMINANCELEVEL_MIN
    return adjust_value(
        round(max_avg / 3, 3),
        constants.LIMIT_ILLUMINANCELEVEL_MIN,
        constants.LIMIT_ILLUMINANCELEVEL_MAX)


def get_limit_value(service_type: str, attribute_name: str, history_values: dict):
    """Returns the limit value that indicates that the streetlight is on."""
    max_avg = get_max_avg(history_values)

    if attribute_name == "intensity":
        return get_intensity_limit_value(service_type, max_avg)
    if attribute_name == "activePower":
        return get_activepower_limit_value(max_avg)
    if attribute_name == "voltage":
        return get_voltage_limit_value(service_type, max_avg)
    if attribute_name == "illuminanceLevel":
        return get_illuminancelevel_limit_value(max_avg)
    if attribute_name == "powerState":
        return "on"
    return None


def get_empty_history_dict():
    """Returns a dictionary used as initial value for history values."""
    temp = {}
    for hour in range(0, 24):
        temp[hour] = {"raw": []}
    return temp


def add_attribute_value(ql_data: collections.OrderedDict, time_string: str, attribute_name: str, attribute_value):
    """Adds new attribute value to the QuantumLeap data dictionary."""
    if time_string not in ql_data:
        ql_data[time_string] = {}
    if attribute_name not in ql_data[time_string]:
        ql_data[time_string][attribute_name] = []

    if isinstance(attribute_value, (int, float)):
        if value_outside_limits(attribute_name, attribute_value):
            return
        attribute_value = round(attribute_value, 3)

    elif isinstance(attribute_value, dict):
        for part_name, part_value in attribute_value.items():
            if isinstance(part_value, (int, float)):
                if value_outside_limits(".".join([attribute_name, part_name]), part_value):
                    return
                attribute_value[part_name] = round(part_value, 3)

    ql_data[time_string][attribute_name].append(attribute_value)


def ql_handle_history_data(history_data: dict):
    """Calculates hour specific mean and standard deviation values for each attribute in the dictionary."""
    for _, history_list in history_data.items():
        for hour in history_list:
            history_list[hour] = get_statistics(history_list[hour]["raw"])


def ql_handle_request_day_data(request_day_data: collections.OrderedDict):
    """Reduces the value lists in the request day data to the mean values."""
    for time_string, attributes in request_day_data.items():
        for attribute_name, attribute_values in attributes.items():
            request_day_data[time_string][attribute_name] = get_mean_value(attribute_values)


def combine_with_history(service_type: str, request_day_values: collections.OrderedDict, history_values: dict):
    """Combines the history data to the request day data (data from /entities endpoint)
       along with the calculated limit values."""
    limit_data = {}
    for time_string, data_values in request_day_values.items():
        hour = int(time_string.split(":")[0])
        for attribute_name, attribute_value in data_values.items():
            history_data = history_values.get(attribute_name, {}).get(hour, {})
            if attribute_name not in limit_data:
                limit_data[attribute_name] = get_limit_value(
                    service_type, attribute_name, history_values.get(attribute_name, {}))

            request_day_values[time_string][attribute_name] = {
                "value": attribute_value,
                "history": history_data,
                "limit": limit_data[attribute_name]
            }
