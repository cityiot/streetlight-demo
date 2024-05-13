"""The Django models used in the streetlight demo."""

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

from django.db import models


class Area(models.Model):
    """Model for streetlight control area information."""
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100, null=True)
    service_type = models.CharField(max_length=20)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    illuminance_off = models.FloatField()
    illuminance_on = models.FloatField()
    illuminance_entity = models.CharField(max_length=100)

    models.UniqueConstraint(fields=["name", "service_type"], name="unique_area")

    def __str__(self):
        return self.name


class Streetlight(models.Model):
    """Model for streetlight or streetlight group information."""
    name = models.CharField(max_length=100)
    group_type = models.CharField(max_length=20)
    address = models.CharField(max_length=100, null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    area1 = models.ForeignKey(Area, on_delete=models.CASCADE)
    area2 = models.ForeignKey(Area, null=True, on_delete=models.CASCADE, related_name="second_area")

    models.UniqueConstraint(fields=["name", "area1"], name="unique_streetlight1")
    models.UniqueConstraint(fields=["name", "area1", "area2"], name="unique_streetlight2")

    def __str__(self):
        return "{} ({})".format(self.name, self.group_type)


class SwitchTime(models.Model):
    """Model for streetlight switch on/off times."""
    low_value = models.TimeField(null=True)
    high_value = models.TimeField(null=True)
    date = models.DateField(null=False)
    switch_type = models.CharField(max_length=10, null=False)  # on, off
    area = models.ForeignKey(Area, on_delete=models.CASCADE, null=True)
    streetlight = models.ForeignKey(Streetlight, on_delete=models.CASCADE, null=True)

    models.UniqueConstraint(fields=["area", "date", "switch_type"], name="unique_area_switch_time")
    models.UniqueConstraint(fields=["streetlight", "date", "switch_type"], name="unique_streetlight_switch_time")

    def __str__(self):
        if self.area is not None:
            entity_str = str(self.area)
        elif self.streetlight is not None:
            entity_str = str(self.streetlight)
        else:
            entity_str = "---"
        return "{}: {}: {}, {}, {}".format(
            entity_str, str(self.date), str(self.low_value), str(self.high_value), str(self.switch_type))


class MeasurementStored(models.Model):
    """Model for holding information whether the streetlight data exists in the database."""
    realtime_values = models.CharField(max_length=10, null=False, default="none")  # full, part, none
    history_values = models.CharField(max_length=10, null=False, default="none")  # full, none
    date = models.DateField(null=False)
    streetlight_entity = models.ForeignKey(Streetlight, on_delete=models.CASCADE, null=False)

    models.UniqueConstraint(fields=["streetlight_entity", "date"], name="unique_measurement_store")

    def __str__(self):
        return "{}, {} ({}, {})".format(
            str(self.streetlight_entity), str(self.date), self.realtime_values, self.history_values)


class Measurement(models.Model):
    """Model for measurement values."""
    name = models.CharField(max_length=100, null=False)
    value_type = models.CharField(max_length=20, default="realtime", null=False)  # realtime, avg, stdev
    value = models.FloatField(null=True)
    timestamp = models.DateTimeField(null=False)
    is_actual = models.FloatField(default=1.0, null=False)  # 0-1, 0 = fully estimated, 1 = no estimation needed
    streetlight_entity = models.ForeignKey(Streetlight, on_delete=models.CASCADE, null=False)

    models.UniqueConstraint(fields=["streetlight_entity", "timestamp", "name"], name="unique_measurement")

    def __str__(self):
        return ", ".join([
            str(self.streetlight_entity), str(self.name), str(self.value_type),
            str(self.value), str(self.timestamp)])


class DayEnergy(models.Model):
    """Model for daily energy values."""
    value = models.FloatField(null=True)
    date = models.DateField(null=False)
    estimated_hours = models.IntegerField(default=0.0, null=False)  # 24=fully estimated, 0=no estimation done
    streetlight_entity = models.ForeignKey(Streetlight, on_delete=models.CASCADE, null=False)

    models.UniqueConstraint(fields=["streetlight_entity", "date"], name="unique_streetlight_energy")

    def __str__(self):
        return ", ".join([
            str(self.streetlight_entity), str(self.date),
            str(self.value), str(self.estimated_hours)])


class DateWarning(models.Model):
    """Model for warnings for streetlights for specific date."""
    not_connected = models.BooleanField(default=False, null=False)
    missing_data_one = models.BooleanField(default=False, null=False)
    missing_data_half = models.BooleanField(default=False, null=False)
    wrong_switch_off_time = models.BooleanField(default=False, null=False)
    wrong_switch_on_time = models.BooleanField(default=False, null=False)
    date = models.DateField(null=False)
    streetlight_entity = models.ForeignKey(Streetlight, on_delete=models.CASCADE, null=False)

    models.UniqueConstraint(fields=["streetlight_entity", "date"], name="unique_warning_collection")

    def __str__(self):
        return ", ".join([
            str(attribute)
            for attribute in [
                self.streetlight_entity,
                self.date,
                self.not_connected,
                self.missing_data_one,
                self.missing_data_half,
                self.wrong_switch_off_time,
                self.wrong_switch_on_time
            ]
        ])
