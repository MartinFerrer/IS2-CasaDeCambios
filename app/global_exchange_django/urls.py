"""URL configuration for global_exchange_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # TODO: eliminar ruta (No usamos el panel admin, solo para ver en desarrollo)
    path("admin_django/", admin.site.urls),
    # Enrutar rutas de las apps
    path("", include("apps.presentacion.urls")),
    path("admin/", include("apps.panel_admin.urls")),
    path("transacciones/", include("apps.transacciones.urls")),
    path("reportes/", include("apps.reportes.urls")),
    path("tauser/", include("apps.tauser.urls")),
    # TODO: evaluar si estos necesitan urls
    path("seguridad/", include("apps.seguridad.urls")),
    path("operaciones/", include("apps.operaciones.urls")),
    path("usuarios/", include("apps.usuarios.urls")),
]
