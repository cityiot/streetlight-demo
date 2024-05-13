"""Helper for loading configuration information."""

SEPARATION_MARK = "="
LOCATIONS = [
    "./env",
    "./env/secrets"
]
CONF_FILES = [
    "django.env",
    "fiware.env",
    "postgres.env"
]


class Configuration():
    """Class containing configuration information for the Django project."""
    def __init__(self):
        self.__configurations = {}
        for location in LOCATIONS:
            for conf_filename in CONF_FILES:
                try:
                    with open("/".join([location, conf_filename]), mode="r", encoding="utf-8") as conf_file:
                        for row in conf_file:
                            row_parts = row.split(SEPARATION_MARK)
                            if len(row_parts) < 2:
                                continue
                            if len(row_parts) == 2:
                                conf_name, conf_value = [part.strip() for part in row_parts]
                            else:
                                conf_name, conf_value = \
                                    [part.strip() for part in [row_parts[0], SEPARATION_MARK.join(row_parts[1:])]]
                            self.__configurations[conf_name] = conf_value
                except IOError:
                    pass

    def get(self, conf_name: str):
        """Returns the stored configuration value. Returns None if the configuration is not found."""
        if conf_name in self.__configurations:
            return self.__configurations[conf_name]
        return None


CONFIGURATION = Configuration()
