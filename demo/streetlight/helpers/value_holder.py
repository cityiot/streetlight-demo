# -*- coding: utf-8 -*-

# Copyright 2020 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module containing a class for holding values with information about whether the value is an estimation."""

class ValueHolder:
    """Class for a value and a flag that tells whether the value is actual value or an estimation."""
    def __init__(self, value, is_actual=1.0):
        self.__value = value
        self.__is_actual = is_actual
        if self.__is_actual < 0.0:
            self.__is_actual = 0.0
        elif self.__is_actual > 1.0:
            self.__is_actual = 1.0

    @property
    def value(self):
        """Returns the value."""
        return self.__value

    @property
    def is_actual(self):
        """Return the flag telling whether the value is actual value (True) or an estimation (False)."""
        return self.__is_actual

    def round(self, decimals: int):
        """Returns a new object in which the value is rounded to the given decimals.
           Only values of type float are rounded."""
        if isinstance(self.value, float):
            return ValueHolder(round(self.value, decimals), self.is_actual)
        return self

    def __str__(self):
        if self.__value is None:
            return ""
        if self.__is_actual:
            return str(self.__value)
        return "{} (estimated)".format(str(self.__value))

    def __repr__(self):
        return str(self)

    def __eq__(self, test_value):
        return self.value == test_value.value and abs(self.is_actual - test_value.is_actual) < 1e-5

    def __lt__(self, test_value):
        return (
            self.value < test_value.value or
            (self.value == test_value.value and self.is_actual < test_value.is_actual)
        )
