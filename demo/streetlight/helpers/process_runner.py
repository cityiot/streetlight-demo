"""Module for running system processess."""

import json
import subprocess

import streetlight.helpers.constants as constants

REACT_WORKDIR = "/usr/src/app/nodejs"
REACT_SCRIPT_DONUT = "donut_marker.js"
DEFAULT_OUTER_RADIUS = 80
DEFAULT_INNER_RADIUS = 60
DEFAULT_IMAGE_SIZE = str(2 * DEFAULT_OUTER_RADIUS + 10)
STATIC_DIRECTORY = "/var/www/static/streetlight"
PUPPETEER_ARGS_JSON = {
    "executablePath": "google-chrome-unstable",
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080"
    ]
}
PUPPETEER_ARGS_STR = json.dumps(PUPPETEER_ARGS_JSON)
FILE_CHECK_COMMAND = "[ -f {filename:} ] && echo 'yes' || echo 'no'"

def get_dashboard_marker_filename(ok_value: int, warning_value: int, error_value: int, extra_text: str):
    """Returns the filename for the dashboard map marker."""
    return constants.DONUT_MARKER_FILENAME.format(
        ok=ok_value,
        warning=warning_value,
        error=error_value,
        text=extra_text
    )


def create_dashboard_icon(ok_value: int, warning_value: int, error_value: int, extra_text: str):
    """Creates a png icon used as a map marker in the dashboard page."""
    props_json = {
        "radius": DEFAULT_OUTER_RADIUS,
        "innerRadius": DEFAULT_INNER_RADIUS,
        "okValue": ok_value,
        "warningValue": warning_value,
        "errorValue": error_value,
        "extraText": extra_text
    }
    filename = get_dashboard_marker_filename(ok_value, warning_value, error_value, extra_text)
    image_command = [
        "node", "cli.js",
        "--filename", filename,
        "--out-dir", STATIC_DIRECTORY,
        "--height", DEFAULT_IMAGE_SIZE,
        "--width", DEFAULT_IMAGE_SIZE,
        "--puppeteer", PUPPETEER_ARGS_STR,
        "--props", json.dumps(props_json),
        REACT_SCRIPT_DONUT
    ]

    try:
        file_check_cmd = FILE_CHECK_COMMAND.format(filename="/".join([STATIC_DIRECTORY, filename]))
        file_check_process = subprocess.run(file_check_cmd, shell=True,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if file_check_process.returncode == 0:
            output = file_check_process.stdout.decode("utf-8").split("\n")[0].strip()
            if output == "yes":
                print("File {} already exists.".format(filename), flush=True)
                return

        image_process = subprocess.run(image_command, cwd=REACT_WORKDIR,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if image_process.returncode == 0:
            print("Created file: {}".format(filename), flush=True)
        else:
            print_out = image_process.stdout.decode("utf-8")
            print("Error while creating file: {} - {}".format(filename, print_out), flush=True)

    except Exception as error:
        print("Error ({}) while creating image file.".format(str(error)), flush=True)
