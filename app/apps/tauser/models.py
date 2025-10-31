"""Modelos para la aplicación tauser.

Este módulo define los modelos relacionados con la gestión de Tausers.
"""

from django.db import models


class Tauser(models.Model):
    """Modelo que representa un Tauser.

    Attributes:
        id (AutoField): Identificador único del tauser (campo automático).
        nombre (CharField): Nombre del tauser (único).
        ubicacion (CharField): Ubicación del tauser.

    """

    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    ubicacion = models.CharField(max_length=200, verbose_name="Ubicación")

    class Meta:
        """Metadatos del modelo Tauser."""

        verbose_name = "Tauser"
        verbose_name_plural = "Tausers"
        ordering = ["nombre"]

    def __str__(self):
        """Retorna la representación en string del Tauser.

        Returns:
            str: Nombre del tauser.

        """
        return self.nombre
