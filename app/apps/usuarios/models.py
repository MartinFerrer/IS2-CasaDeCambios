from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('cajero', 'Cajero'),
        ('supervisor', 'Supervisor'),
    ]

    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='cajero')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'usuario'