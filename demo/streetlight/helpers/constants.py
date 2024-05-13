# -*- coding: utf-8 -*-

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module containing used constants."""

import demo.conf_loader

DONUT_MARKER_FILENAME = "donut_marker_{ok:>04d}_{warning:>04d}_{error:>04d}_{text:s}.png"

TIME_INTERVAL_FOR_SWITCH_TIME = 60
TIME_INTERVAL_FOR_RECENT_DATA = 3600
HISTORY_DAYS = 21
INCLUDE_SECONDS_IN_TIMESTAMPS = False

HOURS_IN_DAY = 24
TIME_CONSTANT = 60
TIME_PARTS = 3
HOUR_CONSTANT = TIME_CONSTANT ** 2
DAY_CONSTANT = HOURS_IN_DAY * TIME_CONSTANT ** 2
MISSING_TIME = "##:##:##"
MISSING_TIME_WITHOUT_SECONDS = "##:##"
MISSING_DATETIME = "--------"
TIME_INTERVAL_SEPARATOR = "-"

WINTER_TIME_OFFSET_S = 7200
SUMMER_TIME_OFFSET_S = 10800

# the starting hour (UTC) for reading the days measurements
# (values larger than 0 means starting from the previous day)
# LIMIT_HOUR = 21
# the maximum number of results in one QuantumLeap query
SIZE_LIMIT = 10000

FULL_STORE_LIMIT_SECONDS = {
    "tampere": DAY_CONSTANT + 8.5 * HOUR_CONSTANT,
    "viinikka": DAY_CONSTANT
}

# limit values that used to determine a single value for determining whether the streetlight is on of off
LIMIT_CURRENT_3PHASE_MIN = 3.0
LIMIT_CURRENT_3PHASE_MAX = 15.0
LIMIT_CURRENT_1PHASE_MIN = 0.1
LIMIT_CURRENT_1PHASE_MAX = 0.25
LIMIT_VOLTAGE_MIN = 1.0
LIMIT_VOLTAGE_MAX = 10.0
LIMIT_POWER_MIN = 2.0
LIMIT_POWER_MAX = 8.0
LIMIT_ILLUMINANCELEVEL_MIN = 0.1
LIMIT_ILLUMINANCELEVEL_MAX = 0.25

# TODO: find out proper default value for this
DEFAULT_VIINIKKA_ENERGY_WITH_FULL_ILLUMINANCE = 50.0
# TODO: find out the proper default voltage value for Tampere data
DEFAULT_TAMPERE_VOLTAGE = 230.0

# minimum and maximum values that are considered real, any values outside the interval are discarded
ATTRIBUTE_VALUE_LIMITS = {
    "intensity": {"low": 0.0, "high": 500.0},
    "voltage": {"low": 0.0, "high": 500.0},
    "activePower": {"low": 0.0, "high": 500.0},
    "illuminanceLevel": {"low": 0.0, "high": 1.0},
    "energy": {"low": 0.0, "high": 10e9},
    "intensity.L1": {"low": 0.0, "high": 500.0},
    "intensity.L2": {"low": 0.0, "high": 500.0},
    "intensity.L3": {"low": 0.0, "high": 500.0},
    "voltage.L1": {"low": 0.0, "high": 500.0},
    "voltage.L2": {"low": 0.0, "high": 500.0},
    "voltage.L3": {"low": 0.0, "high": 500.0},
    "energy.L0": {"low": 0.0, "high": 10e9},
}

VIINIKKA_PRIMARY_ENERGY_ATTRIBUTE = "activePower"
VIINIKKA_SECONDARY_ENERGY_ATTRIBUTE = "illuminanceLevel"
TAMPERE_ENERGY_ATTRIBUTES_MAIN = ["intensity", "voltage"]
TAMPERE_ENERGY_ATTRIBUTES_FULL = [
    "intensity.L1", "intensity.L2", "intensity.L3",
    "voltage.L1", "voltage.L2", "voltage.L3"
]

PREVIOUS_DAY_CHECK_HOURS = 4

DEFAULT_ILLUMINANCE_OFF = 10
DEFAULT_ILLUMINANCE_ON = 15
EXTRA_CABINET = {
    "tampere": "Tampere:Unknown",
    "viinikka": "Viinikka:Unknown"
}
DEFAULT_ILLUMINANCE_DEVICE = {
    "tampere": "WeatherObserved:KV-0217",
    "viinikka": "KV-0125-LS01"
}

VIINIKKA_AREA_ID = 1000
VIINIKKA_AREA_NAME = "Viinikka"
VIINIKKA_AREA_PUBLIC_NAME = "Viinikka"

ORION_ADDRESS = demo.conf_loader.CONFIGURATION.get("ORION_ADDRESS")
QUANTUMLEAP_ADDRESS = demo.conf_loader.CONFIGURATION.get("QUANTUMLEAP_ADDRESS")

FIWARE_HEADERS = {
    "tampere": {
        "FIWARE-Service": demo.conf_loader.CONFIGURATION.get("FIWARE_SERVICE"),
        "FIWARE-ServicePath": demo.conf_loader.CONFIGURATION.get("FIWARE_SERVICE_PATH_TAMPERE"),
        "apikey": demo.conf_loader.CONFIGURATION.get("FIWARE_APIKEY")
    },
    "viinikka": {
        "FIWARE-Service": demo.conf_loader.CONFIGURATION.get("FIWARE_SERVICE"),
        "FIWARE-ServicePath": demo.conf_loader.CONFIGURATION.get("FIWARE_SERVICE_PATH_VIINIKKA"),
        "apikey": demo.conf_loader.CONFIGURATION.get("FIWARE_APIKEY")
    }
}

PHASES = ["L1", "L2", "L3"]

ATTRIBUTES = {
    "tampere": ["intensity", "voltage"],
    "viinikka": ["activePower", "intensity", "voltage", "illuminanceLevel"]
}

ATTRIBUTES_FOR_SWITCH_TIME = {
    "tampere": ["intensity"],
    "viinikka": ["illuminanceLevel"]
}

FULL_STREETLIGHT_ATTRIBUTES = {
    "tampere": ATTRIBUTES["tampere"],
    "viinikka": ATTRIBUTES["viinikka"] + ["OLCtemperature", "poleAngleDrift", "powerState", "status"]
}

ORION_METADATA_TIMESTAMP_ATTRIBUTE = "timestamp"

ATTRIBUTES_FOR_HISTORY_COMPARISON = ["activePower", "intensity", "voltage"]
STDS_FROM_AVERAGE = 3.0
MIN_STDEV = 0.1

OK_LIMIT_TIME = 15 * 60
WARNING_LIMIT_TIME = 30 * 60
TIME_INTERVAL_WARNING_LIMIT = int(2 * 3600)

INFO_LEVEL_STR2INT = {
    "Ok": 1,
    "Warning": 2,
    "Error": 3
}
INFO_LEVEL_INT2STR = {
    1: "Ok",
    2: "Warning",
    3: "Error"
}

ENERGY_ATTRIBUTE = "energy"
ENERGY_PHASE = "L0"  # only for compatibility with the functions made to handle 3-phase currents and voltages

ESTIMATION_LIMIT_HIGH = 0.75
ESTIMATION_LIMIT_LOW = 0.4

SHORT_ATTRIBUTE_NAMES = {
    "activePower": "power",
    "intensity": "current",
    "illuminanceLevel": "level",
    "powerState": "state",
    "voltage": "voltage",
    "OLCtemperature": "OLC temperature",
    "poleAngleDrift": "pole angle drift",
    "status": "status"
}
LONG_ATTRIBUTE_NAMES = {
    "activePower": "power",
    "intensity": "current",
    "illuminanceLevel": "illuminance level",
    "powerState": "power state",
    "voltage": "voltage",
    "OLCtemperature": "OLC temperature",
    "poleAngleDrift": "pole angle drift",
    "status": "status"
}
SHORT_ATTRIBUTE_NAMES_WITH_PHASE = {
    ("intensity", "L1"): "current (L1)",
    ("intensity", "L2"): "current (L2)",
    ("intensity", "L3"): "current (L3)",
    ("voltage", "L1"): "voltage (L1)",
    ("voltage", "L2"): "voltage (L2)",
    ("voltage", "L3"): "voltage (L3)",
    (ENERGY_ATTRIBUTE, ENERGY_PHASE): ENERGY_ATTRIBUTE
}

ATTRIBUTES_DB_FIWARE = {
    "tampere": {
        "current_L1": "intensity.L1",
        "current_L2": "intensity.L2",
        "current_L3": "intensity.L3",
        "voltage_L1": "voltage.L1",
        "voltage_L2": "voltage.L2",
        "voltage_L3": "voltage.L3",
        ENERGY_ATTRIBUTE: ".".join([ENERGY_ATTRIBUTE, ENERGY_PHASE])
    },
    "viinikka": {
        "power": "activePower",
        "current": "intensity",
        "voltage": "voltage",
        "illuminance_level": "illuminanceLevel",
        ENERGY_ATTRIBUTE: ENERGY_ATTRIBUTE
    }
}

ATTRIBUTES_FIWARE_DB = {
    "tampere": {
        "intensity": {
            "L1": "current_L1",
            "L2": "current_L2",
            "L3": "current_L3"
        },
        "voltage": {
            "L1": "voltage_L1",
            "L2": "voltage_L2",
            "L3": "voltage_L3"
        },
        ENERGY_ATTRIBUTE: {
            ENERGY_PHASE: ENERGY_ATTRIBUTE
        }
    },
    "viinikka": {
        "activePower": "power",
        "intensity": "current",
        "voltage": "voltage",
        "illuminanceLevel": "illuminance_level",
        ENERGY_ATTRIBUTE: ENERGY_ATTRIBUTE
    }
}

ATTRIBUTE_COMPACT_DB = {
    "activePower":      "power",
    "intensity":        "current",
    "voltage":          "voltage",
    "illuminanceLevel": "illuminance_level",
    "intensity.L1":     "current_L1",
    "intensity.L2":     "current_L2",
    "intensity.L3":     "current_L3",
    "voltage.L1":       "voltage_L1",
    "voltage.L2":       "voltage_L2",
    "voltage.L3":       "voltage_L3"
}

PUBLIC_AREA_NAMES = {
    "StreetlightControlCabinet:KV-0217": "Area 1",
    "StreetlightControlCabinet:KV-0446": "Area 2",
    "StreetlightControlCabinet:KV-1002": "Area 3",
    "KV-0121": "Viinikka 1",
    "KV-0124": "Viinikka 2",
    "KV-0125": "Viinikka 3",
    "KV-0127": "Viinikka 4",
    "KV-0128": "Viinikka 5",
    "KV-0131": "Viinikka 6"
}

DASHBOARD_LATITUDES = {
    "Area 1": 61.502723,
    "Area 2": 61.534126,
    "Area 3": 61.559759,
    "Viinikka": 61.4528108
}

DASHBOARD_LONGITUDES = {
    "Area 1": 23.750286,
    "Area 2": 23.672483,
    "Area 3": 23.838118,
    "Viinikka": 23.8000158
}
