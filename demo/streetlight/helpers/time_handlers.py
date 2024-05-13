# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module for handling time related calculations and transformations."""

import collections
import datetime
import itertools

import streetlight.models as models
import streetlight.helpers.constants as constants
import streetlight.helpers.datetime_builder as dt_builder
import streetlight.helpers.sun as sun
import streetlight.helpers.value_handlers as value_handlers

SUMMER_TIME_STARTS = [
    datetime.datetime(2017, 3, 26, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2018, 3, 25, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2019, 3, 31, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2020, 3, 29, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2021, 3, 28, 1, tzinfo=datetime.timezone.utc)
]

WINTER_TIME_STARTS = [
    datetime.datetime(2017, 10, 29, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2018, 10, 28, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2019, 10, 27, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2020, 10, 25, 1, tzinfo=datetime.timezone.utc),
    datetime.datetime(2021, 10, 31, 1, tzinfo=datetime.timezone.utc)
]

SEASON_TIME_OFFSET = {
    "summer": datetime.timedelta(seconds=constants.SUMMER_TIME_OFFSET_S),
    "winter": datetime.timedelta(seconds=constants.WINTER_TIME_OFFSET_S)
}
SEASON_TIMEZONE = {
    "summer": datetime.timezone(SEASON_TIME_OFFSET["summer"]),
    "winter": datetime.timezone(SEASON_TIME_OFFSET["winter"])
}
SEASON_LIMIT_HOUR = {
    "summer": (24 - SEASON_TIME_OFFSET["summer"].seconds // constants.HOUR_CONSTANT) % 24,
    "winter": (24 - SEASON_TIME_OFFSET["winter"].seconds // constants.HOUR_CONSTANT) % 24
}


def get_time_season(datetime_object: datetime.datetime):
    """Returns "summer" if summer time is used at the given time in Finland. Otherwise, returns "winter"."""
    for summer_time_start, winter_time_start in zip(SUMMER_TIME_STARTS, WINTER_TIME_STARTS):
        if datetime_object <= summer_time_start:
            return "winter"
        if datetime_object <= winter_time_start:
            return "summer"
    return "summer"


def get_limit_hour(season=None):
    """Returns the appropriate limit hour for the given season (default: "winter").
       The limit hour is the UTC hour from which to start reading data for a given date."""
    if season is None:
        season = "winter"
    return SEASON_LIMIT_HOUR[season]


def datetime_to_local_time(datetime_object: datetime.datetime):
    """Returns the given datetime as object in Finnish local time."""
    time_season = get_time_season(datetime_object)
    timedelta_object = SEASON_TIME_OFFSET[time_season]
    timezone_object = SEASON_TIMEZONE[time_season]
    datetime_object.tzinfo.utcoffset(datetime_object)

    adjusted_datetime = datetime_object + timedelta_object - datetime_object.tzinfo.utcoffset(datetime_object)
    return adjusted_datetime.replace(tzinfo=timezone_object)


def datetime_to_local_time_string(datetime_object: datetime.datetime,
                                  seconds=constants.INCLUDE_SECONDS_IN_TIMESTAMPS):
    """Returns the given datetime as string in Finnish local time."""
    if datetime_object is None:
        return constants.MISSING_DATETIME
    adjusted_datetime = datetime_to_local_time(datetime_object)
    return " ".join([str(adjusted_datetime.date()), str_from_time(adjusted_datetime.time(), seconds)])


def many_datetimes_to_local_time_strings(datetimes, seconds=constants.INCLUDE_SECONDS_IN_TIMESTAMPS):
    """Changes and returns multiple datetimes to Finnish local time."""
    if isinstance(datetimes, datetime.datetime):
        return datetime_to_local_time_string(datetimes, seconds)

    if isinstance(datetimes, dict):
        for dict_key, dict_value in datetimes.items():
            datetimes[dict_key] = many_datetimes_to_local_time_strings(dict_value, seconds)
    elif isinstance(datetimes, list):
        for index, list_item in enumerate(datetimes):
            datetimes[index] = many_datetimes_to_local_time_strings(list_item, seconds)

    return datetimes


def time_to_local_time(time_object_utc: datetime.time, date_object: datetime.date):
    """Returns a time object given in Finnish local time corresponding to the UTC time object."""
    datetime_object = datetime.datetime(
        date_object.year, date_object.month, date_object.day,
        time_object_utc.hour, time_object_utc.minute, time_object_utc.second, tzinfo=datetime.timezone.utc)
    return datetime_to_local_time(datetime_object).time()


def time_string_to_local_time(time_string_utc: str, date_object: datetime.date, seconds=None):
    """Returns the given time string in Finnish local time."""
    if time_string_utc in (constants.MISSING_TIME, constants.MISSING_TIME_WITHOUT_SECONDS):
        if seconds is None:
            return time_string_utc
        if seconds:
            return constants.MISSING_TIME
        return constants.MISSING_TIME_WITHOUT_SECONDS

    time_object = time_from_str(time_string_utc)
    datetime_object = datetime.datetime(
        date_object.year, date_object.month, date_object.day,
        time_object.hour, time_object.minute, time_object.second, tzinfo=datetime.timezone.utc)
    if seconds is None:
        seconds = len(time_string_utc.split(":")) > 2
    return str_from_time(datetime_to_local_time(datetime_object).time(), seconds=seconds)


def many_time_strings_to_local_time(time_strings, date_object: datetime.date,
                                    time_interval=False, seconds=constants.INCLUDE_SECONDS_IN_TIMESTAMPS):
    """Returns all the given time strings in Finnish local time. Assumes that any non-empty string found in the
       given container is a time string (i.e. the string formats are either "hh:mm:ss" or "hh:mm")."""
    if isinstance(time_strings, str) and time_strings != "":
        if time_interval:
            individual_times = time_strings.split(constants.TIME_INTERVAL_SEPARATOR)
            return constants.TIME_INTERVAL_SEPARATOR.join(
                many_time_strings_to_local_time(individual_times, date_object, False, seconds))
        return time_string_to_local_time(time_strings, date_object, seconds)

    if isinstance(time_strings, dict):
        for dict_key, dict_value in time_strings.items():
            time_strings[dict_key] = many_time_strings_to_local_time(dict_value, date_object, time_interval, seconds)
    elif isinstance(time_strings, list):
        for index, list_item in enumerate(time_strings):
            time_strings[index] = many_time_strings_to_local_time(list_item, date_object, time_interval, seconds)

    return time_strings


def date_from_str(date_string: str):
    """Returns a date object based on a string with a format YYYY-MM-DD"""
    if date_string is None:
        return None
    year, month, day = [int(part) for part in date_string.split("-")]
    return datetime.date(year=year, month=month, day=day)


def time_from_str(time_string: str):
    """Returns a time object based on a string with a format hh:mm:ss or hh:mm"""
    if time_string is None or time_string in (constants.MISSING_TIME, constants.MISSING_TIME_WITHOUT_SECONDS):
        return None

    time_parts = [int(part) for part in time_string.split(":")]
    if len(time_parts) == 3:
        return datetime.time(hour=time_parts[0], minute=time_parts[1], second=time_parts[2])
    if len(time_parts) == 2:
        return datetime.time(hour=time_parts[0], minute=time_parts[1])
    return None


def str_from_time(time_object: datetime.time, seconds=constants.INCLUDE_SECONDS_IN_TIMESTAMPS):
    """Returns a time string (hh:mm:ss) or (hh:mm) from the given time object."""
    if time_object is None or not isinstance(time_object, datetime.time):
        if seconds:
            return constants.MISSING_TIME
        return constants.MISSING_TIME_WITHOUT_SECONDS
    if seconds:
        return "{:02d}:{:02d}:{:02d}".format(time_object.hour, time_object.minute, time_object.second)
    return "{:02d}:{:02d}".format(time_object.hour, time_object.minute)


def time_str_from_datetime(datetime_object: datetime.datetime):
    """Returns a time string (hh:mm:ss) from the given datetime object."""
    if datetime_object is None or not isinstance(datetime_object, datetime.datetime):
        return None
    return "{:02d}:{:02d}:{:02d}".format(datetime_object.hour, datetime_object.minute, datetime_object.second)


def get_dt_object(datetime_string: str):
    """Returns a datetime object corresponding to the given datetime string."""
    return dt_builder.DatetimeBuilder.get_object(datetime_string)


def seconds_from_time(time_string: str, time_season: str):
    """Returns the number of seconds from midnight. Uses constants.LIMIT_HOUR to determine the time of midnight
       in local time, i.e. if LIMIT_HOUR is 21, then time_string 02:00 means 5 hours from mignight.
       The time string can be either in hh:mm:ss or hh:mm format."""
    if time_string is None or time_string in ("None", constants.MISSING_TIME, constants.MISSING_TIME_WITHOUT_SECONDS):
        return None
    time_parts = [int(part) for part in time_string.split(":")]
    if len(time_parts) == 2:
        hour, minute = time_parts
        second = 0
    else:
        hour, minute, second = time_parts

    if time_season is not None:
        limit_hour = get_limit_hour(time_season)
        if 0 < limit_hour <= hour:
            hour -= 24
    return 3600 * hour + 60 * minute + second


def get_time_interval_start(time_string: str, time_interval_s: int, time_season: str):
    """Divides the day into intervals of time_interval_s seconds and
       returns the the start of the interval in which time corresponding time_string belongs to."""
    limit_hour = get_limit_hour(time_season)
    seconds = ((seconds_from_time(time_string, time_season) // time_interval_s) * time_interval_s +
               constants.DAY_CONSTANT - limit_hour * constants.HOUR_CONSTANT) % constants.DAY_CONSTANT

    hour = (seconds // (constants.TIME_CONSTANT ** 2) + limit_hour) % 24
    minute = (seconds // constants.TIME_CONSTANT) % constants.TIME_CONSTANT
    second = seconds % constants.TIME_CONSTANT
    return "{hour:02d}:{minute:02d}:{second:02d}".format(
        hour=hour, minute=minute, second=second)


def timestring_from_int(seconds: int, include_seconds_in_result=True):
    """Calculates the time for seconds from mignight and returns it as a time string (hh:mm:ss) or (hh:mm)."""
    if seconds is None:
        if include_seconds_in_result:
            return constants.MISSING_TIME
        return constants.MISSING_TIME_WITHOUT_SECONDS
    if seconds < 0:
        seconds += ((-seconds-1) // constants.DAY_CONSTANT + 1) * constants.DAY_CONSTANT
    if seconds >= constants.DAY_CONSTANT:
        seconds %= constants.DAY_CONSTANT

    hour_and_minute_string = "{h:02d}:{min:02d}".format(
        h=seconds // constants.TIME_CONSTANT**2,
        min=(seconds // constants.TIME_CONSTANT) % constants.TIME_CONSTANT)
    if include_seconds_in_result:
        return "{h_min:s}:{s:02d}".format(
            h_min=hour_and_minute_string, s=seconds % constants.TIME_CONSTANT)
    return hour_and_minute_string


def get_interval_end_time(interval_start_time: str,
                          interval_length_s=constants.TIME_INTERVAL_FOR_RECENT_DATA,
                          include_seconds=constants.INCLUDE_SECONDS_IN_TIMESTAMPS):
    """Returns the string (hh:mm:ss or hh:mm) representing the interval end.
       Example: interval_start_time="05:00", interval_length_s=3600 => returns "06:00"."""
    start_seconds = seconds_from_time(interval_start_time, None)
    if start_seconds is None:
        if include_seconds:
            return constants.MISSING_TIME
        return constants.MISSING_TIME_WITHOUT_SECONDS
    return timestring_from_int(start_seconds + interval_length_s, include_seconds)


def get_time_info(switch_off_check: int, switch_on_check: int):
    """Returns a tuple (info_level, time_info), where info_level is Ok/Warning/Error and
       time_info contains text information about the possible warnings."""
    difference_s = min(abs(switch_off_check), abs(switch_on_check))
    if difference_s <= constants.OK_LIMIT_TIME:
        return "Ok", ""

    if difference_s <= constants.WARNING_LIMIT_TIME:
        info_level = "Warning"
    else:
        info_level = "Error"

    if switch_off_check < 0:
        direction = "switch off too early"
    elif switch_off_check > 0 and abs(switch_off_check) > abs(switch_on_check):
        direction = "switch off too late"
    elif switch_on_check < 0:
        direction = "switch on too early"
    else:
        direction = "switch on too late"

    time_info = "{direction:}: {time_interval:}".format(
        direction=direction,
        time_interval=timestring_from_int(difference_s, constants.INCLUDE_SECONDS_IN_TIMESTAMPS))

    return info_level, time_info


def determine_switch_times(date_string: str, illuminances: dict, times: list, illuminance_limits: list):
    """Determines the expected switch off and switch on times based on the given illuminance values.
       Uses the calculated sunrise and sunset times as limiting values."""
    default_time_interval = 7200
    time_season = get_time_season(get_dt_object(date_string))
    sunrise, sunset = [
        seconds_from_time(sun_time_string, time_season)
        for sun_time_string in sun.sun_times(date_string)]
    switch_off_limits = [sunrise - default_time_interval, sunrise + default_time_interval]
    switch_on_limits = [sunset - default_time_interval, sunset + default_time_interval]

    switch_off = [None, None]
    switch_on = [None, None]
    previous_time = None

    for illuminance_value, time_string in zip(illuminances, times):
        if illuminance_value is None:
            continue
        current_seconds = seconds_from_time(time_string, time_season)

        if (switch_off[1] is None and
                switch_off_limits[0] <= current_seconds <= switch_off_limits[1] and
                illuminance_value >= illuminance_limits["off"]):
            switch_off = [value_handlers.compare2(previous_time, switch_off_limits[0], max), current_seconds]
            continue
        elif switch_off[1] is None and current_seconds > switch_off_limits[1]:
            switch_off = [value_handlers.compare2(previous_time, switch_off_limits[0], max), switch_off_limits[1]]

        if (switch_on[1] is None and
                switch_on_limits[0] <= current_seconds <= switch_on_limits[1] and
                illuminance_value <= illuminance_limits["on"]):
            switch_on = [value_handlers.compare2(previous_time, switch_on_limits[0], max), current_seconds]

        if switch_off[1] is not None and switch_on[1] is not None:
            break
        previous_time = current_seconds

    return (switch_off, switch_off_limits), (switch_on, switch_on_limits)


def switch_time_list_to_dict(switch_time: list):
    """Converts the switch time from list to dictionary."""
    return {
        "low_value": switch_time[0],
        "high_value": switch_time[1]
    }


def store_switch_time(switch_object, switch_time, date_object: datetime.date,
                      switch_type: str, object_type: str):
    """Stores the given switch time to the database."""
    dt_now = datetime.datetime.now()
    if dt_now.date() < date_object:
        return

    if isinstance(switch_time, list):
        switch_time = switch_time_list_to_dict(switch_time)
    for value_type, value in switch_time.items():
        if isinstance(value, str):
            switch_time[value_type] = time_from_str(value)

    if dt_now.date() == date_object:
        switch_time_to_store = {}
        for value_type, value in switch_time.items():
            if value is not None and value <= dt_now.time():
                switch_time_to_store[value_type] = value
    else:
        switch_time_to_store = switch_time

    stored_time = models.SwitchTime.objects.filter(
        **{object_type: switch_object}, date=date_object, switch_type=switch_type)
    if stored_time:
        switch_object = stored_time.get()
        for attr_name, new_value in [(value_type, value)
                                     for value_type, value in switch_time_to_store.items() if value is not None]:
            if getattr(switch_object, attr_name) != new_value:
                setattr(switch_object, attr_name, new_value)
        switch_object.save()
    else:
        switch_object = models.SwitchTime(
            **switch_time, date=date_object, switch_type=switch_type, **{object_type: switch_object})
        switch_object.save()


def distance_from_interval_str(value_start: str, value_end: str, interval_start: str, interval_end: str):
    """Returns the time in seconds from the interval [value_start, value_end] to [interval_start, interval_end]."""
    return value_handlers.distance_from_interval(
        *(seconds_from_time(value, None) for value in (value_start, value_end, interval_start, interval_end)))


def get_interval_len(interval_start: str, interval_end: str):
    """Returns the length of the given time interval in seconds."""
    start_int = seconds_from_time(interval_start, None)
    end_int = seconds_from_time(interval_end, None)
    if start_int is None or end_int is None:
        return -1
    while start_int > end_int:
        start_int -= constants.DAY_CONSTANT
    return end_int - start_int


def get_real_switch_times(current_values: collections.OrderedDict, date_string: str):
    """Returns the real streetlight switch off and switch on times based on the given electricity data."""
    time_season = get_time_season(get_dt_object(date_string))
    real_switch_off = [None, None]
    previous_time = None
    for time_string, attributes in current_values.items():
        if attributes is None:
            continue
        current_seconds = seconds_from_time(time_string, time_season)

        for attribute_name in attributes:
            lights = value_handlers.get_light_status(attributes[attribute_name])
            if lights == "off":
                real_switch_off = [previous_time, current_seconds]
                break
            elif lights == "on":
                previous_time = current_seconds

        if real_switch_off[1] is not None:
            break

    real_switch_on = [None, None]
    previous_time = None
    for time_string, attributes in reversed(current_values.items()):
        if attributes is None:
            continue
        current_seconds = seconds_from_time(time_string, time_season)

        break_loop = False
        for attribute_name in attributes:
            lights = value_handlers.get_light_status(attributes[attribute_name])
            if lights == "off":
                real_switch_on = [current_seconds, previous_time]
                break_loop = True
                break
            elif lights == "on":
                previous_time = current_seconds

        if break_loop:
            break

        if real_switch_on[1] is not None:
            break

    for real_switch_times in [real_switch_off, real_switch_on]:
        for index, real_switch_time in enumerate(real_switch_times):
            if real_switch_time is not None:
                real_switch_times[index] = timestring_from_int(real_switch_time)

    return real_switch_off, real_switch_on


def get_limit_times(date_string: str):
    """Returns the limiting datetime objects as a tuple corresponding to the given date."""
    year, month, day = [int(part) for part in date_string.split("-")]
    limit_hour = get_limit_hour(get_time_season(get_dt_object(date_string)))
    extra_day = 1 if limit_hour > 0 else 0

    date_limit_low = (
        datetime.datetime(
            year=year, month=month, day=day, hour=limit_hour, tzinfo=datetime.timezone.utc) -
        datetime.timedelta(days=extra_day))
    return date_limit_low, date_limit_low + datetime.timedelta(days=1)


def get_hour_range(date_string: str):
    """Return the hour ranges applicable for the given date depending on the call moment."""
    limit_low, limit_high = get_limit_times(date_string)
    dt_now = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc)

    if dt_now >= limit_high:
        return itertools.chain(range(limit_low.hour, 24), range(0, limit_low.hour))
    if dt_now > limit_low:
        if dt_now.day == limit_high.day:
            return itertools.chain(range(limit_low.hour, 24), range(0, dt_now.hour))
        return range(limit_low.hour, dt_now.hour)
    return range(limit_low.hour, limit_low.hour)


def get_previous_day_limit_times(date_string: str):
    """Returns the limiting datetime objects for the hour 20 for the previous day."""
    year, month, day = [int(part) for part in date_string.split("-")]
    limit_hour = get_limit_hour(get_time_season(get_dt_object(date_string)))
    extra_day = 1 if limit_hour > 0 else 0

    return datetime.datetime(year=year, month=month, day=day, hour=limit_hour, tzinfo=datetime.timezone.utc) - \
        datetime.timedelta(days=extra_day, hours=constants.PREVIOUS_DAY_CHECK_HOURS)
