from django.db import models

# Create your models here.

class Permiso(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

class Rol(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)
    permisos = models.ManyToManyField(Permiso, blank=True)

    def __str__(self):
        return self.nombre

class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Aquí se almacena la contraseña encriptada
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    ruc = models.CharField(max_length=11, unique=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    tipo_cliente = models.ForeignKey('TipoCliente', on_delete=models.SET_NULL, null=True, blank=True)
    usuarios = models.ManyToManyField('Usuario', blank=False, related_name='clientes')

    def __str__(self):
        return self.nombre

class TipoCliente(models.Model):
    TIPO_CHOICES = [
        ('minorista', 'Minorista'),
        ('corporativo', 'Corporativo'),
        ('vip', 'VIP'),
    ]
    nombre = models.CharField(max_length=20, choices=TIPO_CHOICES, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.get_nombre_display()

    @staticmethod
    def crear_tipos_por_defecto():
        for tipo, display in TipoCliente.TIPO_CHOICES:
            TipoCliente.objects.get_or_create(nombre=tipo, defaults={'descripcion': display})