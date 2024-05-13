"""The Django views for the streetlight demo."""

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

import datetime
import statistics
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

import streetlight.utils
import streetlight.helpers.constants as constants
import streetlight.helpers.process_runner as process_runner
import streetlight.helpers.result_handlers as result_handlers
import streetlight.helpers.time_handlers as time_handlers

# TODO: implement the fetching of pole angle data
# TODO: implement the storing of pole angle data
# TODO: implement the calculation of warnings for a streetlight(group)
# TODO: implement the area page visualization


def version(request):
    """Returns a json object containing the version number."""
    if request.method == "GET":
        return JsonResponse({"version": "1.2"})
    else:
        return HttpResponseRedirect(reverse('streetlight:index'))


def login_page(request):
    """Login view."""
    return render(request, "streetlight/login.html", {})


def login_user(request):
    """View for logging the user in."""
    if request.method != "POST":
        return HttpResponseRedirect(reverse('streetlight:index'))

    username = request.POST.get("username", "")
    password = request.POST.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return HttpResponseRedirect(reverse('streetlight:index'))
    return HttpResponseRedirect(reverse('streetlight:login_page'))


def logout_user(request):
    """Logout view."""
    logout(request)
    return HttpResponseRedirect(reverse('streetlight:index'))


def index(request, date_string=None):
    """Main dashboard view."""
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('streetlight:login_page'))

    if date_string is None:
        # by default show yesterdays data
        considered_date = datetime.datetime.now() - datetime.timedelta(days=1, hours=8)
    else:
        considered_date = time_handlers.get_dt_object(date_string)

    areas = streetlight.utils.get_areas()
    visible_areas = []
    for area in areas:
        if "Unknown" in area.name:
            continue
        area_streetlights = streetlight.utils.get_streetlights(area.id)
        visible_areas.append({
            "id": area.id,
            "public_name": streetlight.utils.get_public_area_name(area.id),
            "name": area.name.split(":")[-1],
            "service_type": area.service_type,
            "address": area.address.split(",")[-1].strip(),
            "latitude": area.latitude,
            "longitude": area.longitude,
            "count": len(area_streetlights)
        })

    visible_areas.sort(key=lambda x: (x["service_type"], x["public_name"]))

    considered_date_str = "{:>04d}-{:>02d}-{:>02d}".format(
        considered_date.year, considered_date.month, considered_date.day)
    day_energy_tampere = result_handlers.get_service_daily_energy("tampere", considered_date_str)
    day_energy_viinikka = result_handlers.get_service_daily_energy("viinikka", considered_date_str)

    # db_warnings = result_handlers.get_db_warnings(light, date_string)
    # context["db_warnings"] = db_warnings
    # context["no_db_warnings"] = result_handlers.is_no_warnings_set(db_warnings)

    dashboard_areas = []
    viinikka_count = 0
    tampere_error_lights = set()
    viinikka_error_lights = set()
    tampere_warning_lights = set()
    viinikka_warning_lights = set()
    tampere_ok_lights = set()
    viinikka_ok_lights = set()
    for area in visible_areas:
        if area["service_type"] == "tampere":
            area_lights = streetlight.utils.get_streetlights(area["id"])

            area_error_lights = set()
            area_warning_lights = set()
            for area_light in area_lights:
                light_db_warnings = result_handlers.get_db_warnings(area_light, considered_date_str)
                if light_db_warnings is None or light_db_warnings.not_connected:
                    tampere_error_lights.add(area_light.name)
                    area_error_lights.add(area_light.name)
                elif (light_db_warnings.missing_data_half or
                      light_db_warnings.wrong_switch_off_time or light_db_warnings.wrong_switch_on_time):
                    tampere_warning_lights.add(area_light.name)
                    area_warning_lights.add(area_light.name)
                    print("W", area_light.name, light_db_warnings, flush=True)
                else:
                    tampere_ok_lights.add(area_light.name)

            warning_value = len(area_warning_lights)
            error_value = len(area_error_lights)
            ok_value = len(area_lights) - warning_value - error_value
            extra_text = "groups"
            dashboard_areas.append({
                "id": area["id"],
                "public_name": area["public_name"],
                "name": area["name"],
                "service_type": area["service_type"],
                "address": area["address"],
                "latitude": area["latitude"],
                "longitude": area["longitude"],
                "count": area["count"],
                "warningValue": warning_value,
                "errorValue": error_value,
                "icon": process_runner.get_dashboard_marker_filename(ok_value, warning_value, error_value, extra_text),
                "marker_latitude": constants.DASHBOARD_LATITUDES[area["public_name"]],
                "marker_longitude": constants.DASHBOARD_LONGITUDES[area["public_name"]]
            })
            process_runner.create_dashboard_icon(ok_value, warning_value, error_value, extra_text)
        else:
            viinikka_count += area["count"]

    viinikka_lights = streetlight.utils.get_viinikka_streetlights()

    for viinikka_light in viinikka_lights:
        light_db_warnings = result_handlers.get_db_warnings(viinikka_light, considered_date_str)
        if light_db_warnings is None or light_db_warnings.not_connected:
            viinikka_error_lights.add(viinikka_light.name)
        elif (light_db_warnings.missing_data_one or light_db_warnings.missing_data_half):
            #   light_db_warnings.wrong_switch_off_time or light_db_warnings.wrong_switch_on_time):
            viinikka_warning_lights.add(viinikka_light.name)
            print("W", viinikka_light.name, light_db_warnings, flush=True)
        else:
            viinikka_ok_lights.add(viinikka_light.name)

    print("----error", viinikka_error_lights, flush=True)
    print("----warning", viinikka_warning_lights, flush=True)

    warning_value = len(viinikka_warning_lights)
    error_value = len(viinikka_error_lights)
    ok_value = viinikka_count - warning_value - error_value
    extra_text = "lights"
    dashboard_areas.append({
        "id": constants.VIINIKKA_AREA_ID,
        "public_name": "Viinikka",
        "name": "Viinikka",
        "service_type": "viinikka",
        "address": area["address"],
        "latitude": area["latitude"],
        "longitude": area["longitude"],
        "count": viinikka_count,
        "warningValue": warning_value,
        "errorValue": error_value,
        "icon": process_runner.get_dashboard_marker_filename(ok_value, warning_value, error_value, extra_text),
        "marker_latitude": constants.DASHBOARD_LATITUDES["Viinikka"],
        "marker_longitude": constants.DASHBOARD_LONGITUDES["Viinikka"]
    })
    process_runner.create_dashboard_icon(ok_value, warning_value, error_value, extra_text)

    considered_date_str_visible = "{:d}.{:d}.{:d}".format(
        considered_date.day, considered_date.month, considered_date.year)
    context = {
        "date": considered_date_str_visible,
        "date_string": considered_date_str,
        "areas": dashboard_areas,
        "connected_streetlight_groups": len(tampere_ok_lights) + len(tampere_warning_lights),
        "not_connected_streetlight_groups": len(tampere_error_lights),
        "connected_streetlights": len(viinikka_ok_lights) + len(viinikka_warning_lights),
        "not_connected_streetlights": len(viinikka_error_lights),
        "warnings_total": len(tampere_warning_lights) + len(viinikka_warning_lights),
        "warnings_groups": len(tampere_warning_lights),
        "warnings_streetlights": len(viinikka_warning_lights),
        "day_energy": {
            "tampere": result_handlers.daily_energy_as_str(day_energy_tampere),
            "viinikka": result_handlers.daily_energy_as_str(day_energy_viinikka),
            "total": result_handlers.daily_energy_as_str(day_energy_tampere + day_energy_viinikka)
        }
    }
    return render(request, "streetlight/dashboard.html", context)


def index2(request):
    """Main view listing the streetlight control areas.
       This is the old simpler main page."""
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('streetlight:login_page'))

    areas = streetlight.utils.get_areas()
    visible_areas = []
    for area in areas:
        if "Unknown" in area.name:
            continue
        visible_areas.append({
            "id": area.id,
            "public_name": streetlight.utils.get_public_area_name(area.id),
            "name": area.name.split(":")[-1],
            "service_type": area.service_type,
            "address": area.address.split(",")[-1].strip(),
            "latitude": area.latitude,
            "longitude": area.longitude,
            "count": len(streetlight.utils.get_streetlights(area.id))
        })
    visible_areas.sort(key=lambda x: (x["service_type"], x["public_name"]))

    context = {"areas": visible_areas}
    return render(request, "streetlight/index_old.html", context)


def area_info(request, area_id: int):
    """Area view showinf information about the selected area."""
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('streetlight:login_page'))

    context = {}
    if area_id == constants.VIINIKKA_AREA_ID:
        areas = streetlight.utils.get_viinikka_areas()
        if not areas:
            context["error"] = "Viinikka area not found."
        else:
            context["area_id"] = area_id
            context["name"] = constants.VIINIKKA_AREA_NAME
            context["public_name"] = constants.VIINIKKA_AREA_PUBLIC_NAME
            context["service_type"] = "viinikka"

            area_address = [one_area.address.split(",")[-1].strip() for one_area in areas if one_area.address != ""]
            area_latitude = [one_area.latitude for one_area in areas if one_area.latitude > 0]
            area_longitude = [one_area.longitude for one_area in areas if one_area.longitude > 0]
            context["area_locations"] = [
                {
                    "address": one_address,
                    "latitude": one_latitude,
                    "longitude": one_longitude
                }
                for one_address, one_latitude, one_longitude in zip(area_address, area_latitude, area_longitude)
            ]
            context["map_center_latitude"] = statistics.mean(area_latitude)
            context["map_center_longitude"] = statistics.mean(area_longitude)

            lights = streetlight.utils.get_viinikka_streetlights()

    else:
        area = streetlight.utils.get_area(area_id)
        if area is None:
            context["error"] = "Area with id {} not found.".format(area_id)
        else:
            context["area_id"] = area_id
            context["name"] = area.name.split(":")[-1]
            context["public_name"] = streetlight.utils.get_public_area_name(
                area_id)
            context["service_type"] = area.service_type

            context["address"] = area.address.split(",")[-1].strip()
            context["latitude"] = area.latitude
            context["longitude"] = area.longitude
            context["area_locations"] = [{
                "address": [area.address.split(",")[-1].strip()],
                "latitude": [area.latitude],
                "longitude": [area.longitude]
            }]
            context["map_center_latitude"] = area.latitude
            context["map_center_longitude"] = area.longitude

            lights = streetlight.utils.get_streetlights(area_id)

    if "error" not in context:
        latest_timestamps = time_handlers.many_datetimes_to_local_time_strings(
            streetlight.utils.get_latest_streetlight_timestamps(lights))
        light_list = []
        for light in lights:
            light_list.append({
                "id": light.id,
                "area": area_id,
                "name": light.name.split(":")[-1],
                "address": light.address.split(",")[-1].strip(),
                "latitude": light.latitude,
                "longitude": light.longitude,
                "timestamp": latest_timestamps[light.name]
            })
        light_list.sort(key=lambda x: x["name"])

        context["lights"] = light_list
        context["count"] = len(light_list)

    return render(request, "streetlight/area_info.html", context)


def light_info(request, area_id: int, light_id: int):
    """Streetlight view showing information about individual streetlight or group."""
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('streetlight:login_page'))

    context = {}
    if area_id == constants.VIINIKKA_AREA_ID:
        areas = streetlight.utils.get_viinikka_areas()
        if not areas:
            context["error"] = "Viinikka area not found."

    if "error" not in context:
        light, area = streetlight.utils.get_streetlight(area_id, light_id)

        if area is None:
            context["error"] = "Area with id {} not found.".format(area_id)
        elif light is None:
            area_name = area.name.split(":")[-1]
            context["error"] = "Light with id {} not found in area {}.".format(
                light_id, area_name)
            context["area_id"] = area_id
            context["area_name"] = area_name
        else:
            context["area_public_name"] = streetlight.utils.get_public_area_name(
                area_id)
            context["light_id"] = light.id
            context["name"] = light.name.split(":")[-1]
            context["service_type"] = area.service_type
            context["address"] = light.address.split(",")[-1].strip()
            context["latitude"] = light.latitude
            context["longitude"] = light.longitude
            context["area_id"] = area_id
            context["area_name"] = area.name.split(":")[-1]

            latest_values = streetlight.utils.get_latest_streetlight_values(light)
            for value_index, attribute in enumerate(latest_values):
                latest_values[value_index]["timestamp"] = \
                    time_handlers.datetime_to_local_time_string(
                        attribute["timestamp"])
            context["attributes"] = latest_values

            dt_now = datetime.datetime.now()
            context["date_string"] = "{:04}-{:02}-{:02}".format(
                dt_now.year, dt_now.month, dt_now.day)

    return render(request, "streetlight/light_info.html", context)


def fetch_info(request):
    """Redirects the data fetch request to the appropriate view."""
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('streetlight:login_page'))
    if request.method != "POST":
        return HttpResponseRedirect(reverse('streetlight:index'))

    try:
        area_id = int(request.POST.get("area_id", -1))
    except ValueError:
        area_id = -1

    try:
        light_id = request.POST.get("light_id", -1)
        if light_id != "all":
            light_id = int(light_id)
    except ValueError:
        light_id = -1

    date_string = request.POST.get("date_string", "")

    if date_string == "":
        if light_id == "all" or light_id < 0:
            if area_id < 0:
                return HttpResponseRedirect(reverse('streetlight:index'))
            return HttpResponseRedirect(reverse('streetlight:area_info', args=[area_id]))
        return HttpResponseRedirect(reverse('streetlight:light_info', args=[area_id, light_id]))
    if light_id == -1 and area_id == -1:
        return redirect("index/{}".format(date_string))
    return redirect("{}/{}/{}".format(area_id, light_id, date_string))


def all_light_date_info(request, area_id: int, date_string: str):
    """A view for showing compact information about the selected area on the selected date."""
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('streetlight:login_page'))

    log_level = "info"
    # time_interval = constants.TIME_INTERVAL_FOR_RECENT_DATA
    # history_days = constants.HISTORY_DAYS

    context = {}
    if area_id == constants.VIINIKKA_AREA_ID:
        areas = streetlight.utils.get_viinikka_areas()
        if not areas:
            context["error"] = "Viinikka area not found."
        else:
            area = areas.first()
            name = constants.VIINIKKA_AREA_NAME
            public_name = constants.VIINIKKA_AREA_PUBLIC_NAME
            area_address = [one_area.address.split(",")[-1].strip() for one_area in areas if one_area.address != ""]
            area_latitude = [one_area.latitude for one_area in areas if one_area.latitude > 0]
            area_longitude = [one_area.longitude for one_area in areas if one_area.longitude > 0]
            map_center_latitude = statistics.mean(area_latitude)
            map_center_longitude = statistics.mean(area_longitude)

            lights = streetlight.utils.get_viinikka_streetlights()

    else:
        area = streetlight.utils.get_area(area_id)
        if area is None:
            context["error"] = "Area with id {} not found.".format(area_id)
        else:
            name = area.name.split(":")[-1]
            public_name = streetlight.utils.get_public_area_name(area_id)
            area_address = [area.address.split(",")[-1].strip()]
            area_latitude = [area.latitude]
            area_longitude = [area.longitude]
            map_center_latitude = area_latitude[0]
            map_center_longitude = area_longitude[0]

            lights = streetlight.utils.get_streetlights(area_id)

    if "error" not in context:
        expected_switch_times = result_handlers.fetch_switch_times(area, date_string)

        light_list = result_handlers.get_all_lights_info_simple(
            lights, date_string, expected_switch_times, log_level)  # , time_interval, history_days)
        light_list.sort(key=lambda x: x["name"])

        latest_timestamps = time_handlers.many_datetimes_to_local_time_strings(
            streetlight.utils.get_latest_streetlight_timestamps(lights))
        for light_index, light in enumerate(light_list):
            light_list[light_index]["timestamp"] = latest_timestamps[light["full_name"]]

    error_light_count = 0
    warning_light_count = 0
    ok_light_count = 0
    for light_index, light in enumerate(light_list):
        print(light_index, light["name"], len(light_list), flush=True)
        light_object, _ = streetlight.utils.get_streetlight(area_id, light["id"])
        light_db_warnings = result_handlers.get_db_warnings(light_object, date_string)
        if light_db_warnings is None or light_db_warnings.not_connected:
            light_list[light_index]["marker"] = {"error": True}
            error_light_count += 1
        elif light_db_warnings.missing_data_half:
            light_list[light_index]["marker"] = {"warning": True}
            warning_light_count += 1
        else:
            light_list[light_index]["marker"] = {"ok": True}
            ok_light_count += 1

    area_day_energy = result_handlers.get_area_daily_energy(lights, date_string)

    # change the time strings to local Finnish time
    date_object = time_handlers.date_from_str(date_string)
    expected_switch_times = time_handlers.many_time_strings_to_local_time(
        expected_switch_times, date_object)
    for list_index, light_item in enumerate(light_list):
        light_list[list_index]["info"]["switch_off"], light_list[list_index]["info"]["switch_on"] = \
            time_handlers.many_time_strings_to_local_time(
                [light_item["info"]["switch_off"], light_item["info"]["switch_on"]],
                date_object, time_interval=True)

    context = {
        "area_id": area_id,
        "name": name,
        "public_name": public_name,
        "service_type": area.service_type,
        "area_locations": [
            {
                "address": one_address,
                "latitude": one_latitude,
                "longitude": one_longitude,
            }
            for one_address, one_latitude, one_longitude in zip(area_address, area_latitude, area_longitude)
        ],
        "map_center_latitude": map_center_latitude,
        "map_center_longitude": map_center_longitude,
        "expected_switch_off": constants.TIME_INTERVAL_SEPARATOR.join(expected_switch_times[0]),
        "expected_switch_on": constants.TIME_INTERVAL_SEPARATOR.join(expected_switch_times[1]),
        "lights": light_list,
        "count": len(light_list),
        "ok_count": ok_light_count,
        "warning_count": warning_light_count,
        "error_count": error_light_count,
        "date_string": date_string,
        "area_day_energy_str": result_handlers.daily_energy_as_str(area_day_energy)
    }

    return render(request, "streetlight/all_date_info.html", context)


def light_date_info(request, area_id: int, light_id: int, date_string: str):
    """View for showing detailed information about the selected streetlight on the selected date."""
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('streetlight:login_page'))

    log_level = "info"
    # time_interval = constants.TIME_INTERVAL_FOR_RECENT_DATA
    # history_days = constants.HISTORY_DAYS

    context = {}
    if area_id == constants.VIINIKKA_AREA_ID:
        areas = streetlight.utils.get_viinikka_areas()
        if not areas:
            context["error"] = "Viinikka area not found."

    if "error" not in context:
        light, area = streetlight.utils.get_streetlight(area_id, light_id)

        context = {}
        if area is None:
            context["error"] = "Area with id {} not found.".format(area_id)
        if light is None:
            context["error"] = "Light with id {} not found in area {}.".format(light_id, area.name)
            context["area_id"] = area_id
            context["area_name"] = area.name.split(":")[-1]
        else:
            context = result_handlers.get_light_info(
                area, light, date_string, log_level)  # , time_interval, history_days)
            db_warnings = result_handlers.get_db_warnings(light, date_string)
            context["db_warnings"] = db_warnings
            context["no_db_warnings"] = result_handlers.is_no_warnings_set(db_warnings)

            # change the time strings to local Finnish time
            date_object = time_handlers.date_from_str(date_string)
            (
                context["expected_switch_off"],
                context["expected_switch_on"],
                context["streetlight"]["switch"]["switch_off"],
                context["streetlight"]["switch"]["switch_on"]
            ) = time_handlers.many_time_strings_to_local_time(
                [
                    context["expected_switch_off"],
                    context["expected_switch_on"],
                    context["streetlight"]["switch"]["switch_off"],
                    context["streetlight"]["switch"]["switch_on"]],
                date_object, time_interval=True)

            context["graphdata"] = []
            for list_index, entry in enumerate(context["streetlight"]["data"]["entries"]):
                local_time = time_handlers.many_time_strings_to_local_time(
                    entry.get("time", ""), date_object, time_interval=True)
                if local_time:
                    local_hour = str(int(local_time[:2]))
                    context["streetlight"]["data"]["entries"][list_index]["time"] = local_time
                    energy_entry = entry.get("energy", None)

                    if energy_entry is not None:
                        context["graphdata"].append({
                            "x": local_hour,
                            "y": energy_entry.value,
                            "color": energy_entry.is_actual
                        })

            context["area_public_name"] = streetlight.utils.get_public_area_name(area_id)
            context["date_string"] = date_string
            context["light_id"] = light.id
            context["name"] = light.name.split(":")[-1]
            context["service_type"] = area.service_type
            context["address"] = light.address.split(",")[-1].strip()
            context["latitude"] = light.latitude
            context["longitude"] = light.longitude
            context["area_id"] = area_id
            context["area_name"] = area.name.split(":")[-1]

    return render(request, "streetlight/light_date_info.html", context)
