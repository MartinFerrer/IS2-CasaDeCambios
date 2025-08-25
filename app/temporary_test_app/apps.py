from django.apps import AppConfig


class TemporaryTestAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'temporary_test_app'
