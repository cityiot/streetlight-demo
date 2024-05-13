# Copyright 2019 Tampere University
# This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
# This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

python -u -m manage makemigrations
python -u -m manage migrate
python -u -m manage add_users

# for now just download the bundled resources required for the application
while read resource;
do
    url="$(cut -d' ' -f1 <<<$resource)"
    file_path="static/$(cut -d' ' -f2 <<<$resource)"
    file_name="$(cut -d' ' -f3 <<<$resource)"
    [ -f $file_path/$file_name ] && echo "File $file_name already exists." || {
        mkdir -p $file_path;
        curl -X GET $url > $file_path/$file_name;
    }
done < js_resources.txt

python -u -m manage collectstatic --noinput
python -u -m manage runserver 0.0.0.0:8000
