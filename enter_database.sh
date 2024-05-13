# Copyright 2020 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

docker exec -it $(docker ps | grep demo_streetlight_db | awk '{print $1'}) psql -d streetlightdemo -U cityiot
