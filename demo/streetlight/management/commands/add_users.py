"""Module containing a command for adding users to a Django project."""
import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import demo.conf_loader as conf_loader


def print_command_help():
    """Prints usage information for the add_users command."""
    print("Usage:", "add_users", "<USER_INFO_FILENAME>")


class Command(BaseCommand):
    """Command for adding users to a Django project."""
    def handle(self, *args, **options):
        """Handle function for adding users to a Django project."""
        requested_users = []
        try:
            filename = conf_loader.CONFIGURATION.get("USER_INFO_FILENAME")
            with open(filename, mode="r", encoding="utf-8") as user_file:
                requested_users = json.load(user_file)
        except IndexError:
            print_command_help()
        except IOError:
            print_command_help()

        for requested_user in requested_users:
            username = requested_user.get("username", None)
            password = requested_user.get("password", None)
            if username and password:
                user_query = User.objects.filter(username=username)
                if user_query:
                    user_object = user_query.get()
                else:
                    user_object = User.objects.create_user(username)
                user_object.set_password(password)
                user_object.is_superuser = requested_user.get("is_superuser", False)
                user_object.is_staff = requested_user.get("is_staff", False)
                user_object.save()

                if user_query:
                    print("Updated user:", username)
                else:
                    print("Added user:", username)
