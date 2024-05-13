# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module for getting the sunrise and sunset times."""

import datetime

import astral

DEFAULT_CITY = astral.Location(("Tampere", "Finland", 61.4978, 23.7610, "Europe/Helsinki", 0))


def sun_times(date_string: str, city=DEFAULT_CITY):
    """Returns the sunrise and and sunset times for the selected date."""
    year, month, day = [int(part) for part in date_string.split("-")]
    selected_date = datetime.date(year=year, month=month, day=day)
    sunrise = city.sunrise(date=selected_date, local=False)
    sunset = city.sunset(date=selected_date, local=False)

    sunrise_string = "{hour:02d}:{minute:02d}:{second:02d}".format(
        hour=sunrise.hour,
        minute=sunrise.minute,
        second=sunrise.second)
    sunset_string = "{hour:02d}:{minute:02d}:{second:02d}".format(
        hour=sunset.hour,
        minute=sunset.minute,
        second=sunset.second)

    return sunrise_string, sunset_string
