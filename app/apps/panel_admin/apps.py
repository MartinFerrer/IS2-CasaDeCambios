"""Módulo de configuración para la aplicación del panel administrativo."""

from django.apps import AppConfig


class AdminConfig(AppConfig):
    """Clase de configuración de aplicación de panel administrador."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.panel_admin"
