from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

# users/apps.py
def ready(self):
    import users.signals