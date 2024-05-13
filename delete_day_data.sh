# Copyright 2020 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

postgres_container=$(docker ps | grep demo_streetlight_db | awk '{print $1'})
postgres_db=$(cat demo/env/postgres.env | grep POSTGRES_DB | cut -d'=' -f 2)
postgres_user=$(cat demo/env/postgres.env | grep POSTGRES_USER | cut -d'=' -f 2)
docker_command="docker exec -it $postgres_container psql -d $postgres_db -U $postgres_user"

$docker_command -c "DELETE FROM streetlight_dayenergy WHERE date = '$1'"
$docker_command -c "DELETE FROM streetlight_datewarning WHERE date = '$1'"
$docker_command -c "DELETE FROM streetlight_measurementstored WHERE date = '$1'"
$docker_command -c "DELETE FROM streetlight_switchtime WHERE date = '$1'"
$docker_command -c "DELETE FROM streetlight_measurement WHERE timestamp >= '$1T00:00:00Z' AND timestamp <= '$1T23:59:59.999Z'"
