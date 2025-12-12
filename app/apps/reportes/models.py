"""Modelos para la aplicación de reportes.

Este módulo define modelos proxy para registrar permisos personalizados
relacionados con reportes y dashboards financieros.
"""

from django.db import models


class Reporte(models.Model):
    """Modelo proxy para gestionar permisos de reportes.

    Este modelo no crea una tabla en la base de datos, solo sirve para
    registrar permisos personalizados relacionados con reportes.
    """

    class Meta:
        """Configuración de metadatos para el modelo Reporte."""

        managed = False  # No crear tabla en la base de datos
        default_permissions = ()  # No crear permisos CRUD por defecto
        permissions = [
            ("view_reportes", "Ver reportes y dashboards"),
            ("generate_reportes", "Generar reportes"),
        ]
