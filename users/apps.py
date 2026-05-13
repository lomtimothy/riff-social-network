from django.apps import AppConfig

class UsersConfig(AppConfig):
    name = 'users'

    # Esta función debe tener 4 espacios para pertenecer a la clase
    def ready(self):
        import users.signals