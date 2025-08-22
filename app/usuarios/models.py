'''This file is where you define the data models for the module. Models represent database tables and define the fields and behaviors of the data you want to store.
Each model is a subclass of django.db.models.Model and typically includes attributes that map to database fields.'''
####################inicio borrar
#para roles
#extender user
from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    # Aquí puedes agregar campos adicionales si es necesario
    # Por ejemplo, un campo para el número de teléfono
    telefono = models.CharField(max_length=15, blank=True, null=True)
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
    def __str__(self):
        return self.username
    
    '''
    Después dice que en settings.py hay que agregar:
    AUTH_USER_MODEL = 'usuarios.Usuario'
    Esto le dice a Django que use el modelo Usuario como el modelo de usuario por defecto.
    También dice que hay que hacer migraciones:
    docker-compose run web python manage.py makemigrations usuarios
    docker-compose run web python manage.py migrate
    '''

    '''
    para roles
    usar django groups para roles
    agregar custom permissions si es necesario, groups es suficiente para roles básicos
    codificar crud para roles y usuarios más adelante
    en este punto ya convendría hacer un commit...
    '''
    #fin de los comentarios sobre el modulo de Seguridad y Autenticación
    #############################fin borrar