"""The routes used in the streetlight demo."""

# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

from django.urls import path

from . import views

app_name = 'streetlight'
urlpatterns = [
    path("", views.index, name="index"),
    path("index", views.index, name="index_alt"),
    path("index/<date_string>", views.index, name="index_date"),
    path("index2", views.index2, name="index2"),
    path("version", views.version, name="version"),
    path("login", views.login_page, name="login_page"),
    path("logout", views.logout_user, name="logout_user"),
    path("login_user", views.login_user, name="login_user"),
    path("info", views.fetch_info, name="fetch_info"),
    path("<int:area_id>", views.area_info, name="area_info"),
    path("<int:area_id>/<int:light_id>", views.light_info, name="light_info"),
    path("<int:area_id>/all/<date_string>", views.all_light_date_info, name="all_light_date_info"),
    path("<int:area_id>/<int:light_id>/<date_string>", views.light_date_info, name="light_date_info")
]
