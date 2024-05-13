# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module for converting and storing timestamps received from QuantumLeap to datetime objects."""

import datetime


class DatetimeBuilder:
    """Class for converting and storing QuantumLeap timestamps datetime objects."""
    timezone = "+0000"
    date_format = "%Y-%m-%d%z"
    datetime_format = "%Y-%m-%dT%H:%M:%S%z"
    __datetime_dictionary = {}

    @classmethod
    def get_object(cls, datetime_string: str) -> datetime.datetime:
        """Return the datetime object corresponding to the given string. Uses 1s accuracy."""
        stripped_datetime_string = datetime_string.split(".")[0]
        if "T" in stripped_datetime_string:
            dt_format = cls.datetime_format
        else:
            dt_format = cls.date_format

        if stripped_datetime_string not in cls.__datetime_dictionary:
            cls.__datetime_dictionary[stripped_datetime_string] = \
                datetime.datetime.strptime("".join([stripped_datetime_string, cls.timezone]), dt_format)
        return cls.__datetime_dictionary[stripped_datetime_string]

    @classmethod
    def len_stored_objects(cls):
        """Returns the number of stored datetime objects."""
        return len(cls.__datetime_dictionary)
