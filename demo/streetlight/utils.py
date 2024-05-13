# -*- coding: utf-8 -*-
"""Module containing a collection of helper/utility functions for the streetlight demo."""

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

from django.db.models import Q
from django.db.models.query import QuerySet

import streetlight.helpers.constants as constants
import streetlight.helpers.http_helpers as http_helpers
import streetlight.models as models


def get_public_area_name(area_id: int):
    """Returns the area name shown in web page for the selected area."""
    if area_id == constants.VIINIKKA_AREA_ID:
        return constants.VIINIKKA_AREA_PUBLIC_NAME

    area = models.Area.objects.filter(id=area_id)
    if not area:
        return "Unknown"

    area = area.first()
    if area.name in constants.PUBLIC_AREA_NAMES:
        return constants.PUBLIC_AREA_NAMES[area.name]
    return "{service_type:} {area_id:d}".format(service_type=area.service_type.capitalize(), area_id=area_id)


def update_streetlight_entity(area_object: models.Area, streetlight_entity: dict):
    """Updates the streetlight object in the database."""
    if not area_object or not streetlight_entity:
        return

    streetlight_address = streetlight_entity["address"]
    streetlight_full_address = ", ".join([
        streetlight_address.get("addressCountry", ""),
        streetlight_address.get("addressLocality", ""),
        streetlight_address.get("streetAddress", "")])
    streetlight_location = streetlight_entity["location"].get("coordinates", [0.0, 0.0])

    old_streetlight = models.Streetlight.objects.filter(name=streetlight_entity["id"])

    if not old_streetlight:
        streetlight_object = models.Streetlight(
            name=streetlight_entity["id"],
            group_type=streetlight_entity["type"],
            address=streetlight_full_address,
            latitude=streetlight_location[1],
            longitude=streetlight_location[0],
            area1=area_object,
            area2=None
        )
    else:
        streetlight_object = old_streetlight.first()
        for attr_name, new_value in [
                ("group_type", streetlight_entity["type"]),
                ("address", streetlight_full_address),
                ("latitude", streetlight_location[1]),
                ("longitude", streetlight_location[0]),
                ("area2", area_object)]:
            if getattr(streetlight_object, attr_name) != new_value:
                setattr(streetlight_object, attr_name, new_value)

    streetlight_object.save()


def update_area(area_object: models.Area):
    """Updates the streetlight entities in the database using information from Orion."""
    if not area_object:
        return

    new_streetlights = http_helpers.get_streetlights(area_object.service_type, area_object.name)
    for streetlight_entity in new_streetlights:
        update_streetlight_entity(area_object, streetlight_entity)
    print("Updated area", area_object.name, flush=True)


def update_entities():
    """Updates the area and streetlight entities in the database using information from Orion."""
    old_areas = models.Area.objects.all()

    print("Updating entities", flush=True)
    new_areas = http_helpers.get_areas()

    for area_name, area_info in new_areas.items():
        old_area = old_areas.filter(name=area_name)

        address = area_info["address"]
        full_address = ", ".join([
            address.get("addressCountry", ""),
            address.get("addressLocality", ""),
            address.get("streetAddress", "")])
        location = area_info["location"].get("coordinates", [0.0, 0.0])

        if not old_area:
            area_object = models.Area(
                name=area_name,
                address=full_address,
                service_type=area_info["service_type"],
                latitude=location[1],
                longitude=location[0],
                illuminance_off=area_info["illuminance_limits"]["off"],
                illuminance_on=area_info["illuminance_limits"]["on"],
                illuminance_entity=area_info["illuminance_entity"]
            )
        else:
            area_object = old_area.first()
            for attr_name, new_value in [
                    ("address", full_address),
                    ("service_type", area_info["service_type"]),
                    ("latitude", location[1]),
                    ("longitude", location[0]),
                    ("illuminance_off", area_info["illuminance_limits"]["off"]),
                    ("illuminance_on", area_info["illuminance_limits"]["on"]),
                    ("illuminance_entity", area_info["illuminance_entity"])]:
                if getattr(area_object, attr_name) != new_value:
                    setattr(area_object, attr_name, new_value)

        area_object.save()

        for streetlight_entity in area_info["streetlights"]:
            update_streetlight_entity(area_object, streetlight_entity)

    print("Updated entities.", flush=True)


def get_areas():
    """Returns the streetlight control area objects.
       If the list is empty, tries to fetch the information from Orion."""
    old_areas = models.Area.objects.all()
    if not old_areas:
        update_entities()
        old_areas = models.Area.objects.all()

    return old_areas


def get_viinikka_areas():
    """Returns the viinikka control area objects."""
    old_areas = models.Area.objects.filter(service_type="viinikka")
    if not old_areas:
        update_entities()
        old_areas = models.Area.objects.filter(service_type="viinikka")

    return old_areas


def get_area(area_identifier, identifier_name="id", update=True):
    """Returns a streetlight control area object.
       If the area is not found, tries to fetch the information from Orion."""
    old_area = models.Area.objects.filter(**{identifier_name: area_identifier})
    if update and not old_area:
        update_entities()
        old_area = models.Area.objects.filter(**{identifier_name: area_identifier})

    if old_area:
        return old_area.first()
    return None


def get_streetlights(area_id: int, update=True):
    """Returns the streetlight objects in the selected area.
       If the area is not found, tries to fetch the information from Orion."""
    area = get_area(area_id, update=update)

    if area:
        return models.Streetlight.objects.filter(Q(area1=area) | Q(area2=area))
    return None


def get_service_streetlights(service_type: str):
    """Returns all the streetlight objects for the given service type existing in the database."""
    areas = models.Area.objects.filter(service_type=service_type)
    streetlight_lists = [models.Streetlight.objects.filter(area1=area) for area in areas]
    return models.Streetlight.objects.none().union(*streetlight_lists)


def get_viinikka_streetlights():
    """Returns all Viinikka streetlight objects."""
    viinikka_areas = get_viinikka_areas()
    viinikka_streetlights = models.Streetlight.objects.none()
    for viinikka_area in viinikka_areas:
        viinikka_streetlights |= models.Streetlight.objects.filter(area1=viinikka_area.id)
    return viinikka_streetlights


def get_streetlight(area_identifier, entity_identifier, identifier_name="id", update=True):
    """Returns a tuple: (streetlight object, area_object)."""
    if area_identifier == constants.VIINIKKA_AREA_ID and identifier_name == "id":
        # in the case of the whole Viinikka area, no updates will be done
        entities = models.Streetlight.objects.filter(**{identifier_name: entity_identifier})
        if entities:
            for entity in entities:
                if entity.area1.service_type == "viinikka":
                    return entity, entity.area1
        return None, None

    area = get_area(area_identifier, identifier_name, update=update)
    if area is None:
        return None, None

    entity = models.Streetlight.objects.filter(**{identifier_name: entity_identifier, "area1": area})
    if not entity:
        entity = models.Streetlight.objects.filter(**{identifier_name: entity_identifier, "area2": area})
        if update and not entity:
            update_area(area)
            entity = models.Streetlight.objects.filter(**{identifier_name: entity_identifier, "area1": area})
            if not entity:
                entity = models.Streetlight.objects.filter(**{identifier_name: entity_identifier, "area2": area})

    if entity:
        return entity.first(), area
    return None, area


def get_streetlight_without_area(entity_identifier, identifier_name="id"):
    """Returns a streetlight object from the database."""
    entity = models.Streetlight.objects.filter(**{identifier_name: entity_identifier})

    if entity:
        return entity.first()
    return None


def get_latest_streetlight_timestamps(entities: QuerySet):
    """Returns a dictionary containing the latest timestamp (as string) for each given streetlight entity."""
    if not entities:
        return {}

    service_type = entities.first().area1.service_type
    entity_names = [entity.name for entity in entities]
    return {
        entity_name: timestamp
        for entity_name, timestamp in http_helpers.get_latest_orion_timestamps(service_type, entity_names).items()
    }


def get_latest_streetlight_values(entity: models.Streetlight):
    """Returns the latest attribute values from Orion for the given entity."""
    if not entity:
        return {}

    service_type = entity.area1.service_type
    return http_helpers.get_latest_orion_values(
        service_type, entity.name, constants.FULL_STREETLIGHT_ATTRIBUTES[service_type])
