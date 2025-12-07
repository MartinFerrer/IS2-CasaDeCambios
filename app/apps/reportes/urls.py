"""URLs para la app de reportes"""

from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    # Reporte HTML para modal
    path("transacciones/generar/", views.generar_reporte_html, name="generar_reporte_html"),
    # Descargas
    path("transacciones/descargar/pdf/", views.descargar_reporte_pdf, name="descargar_reporte_pdf"),
    path("transacciones/descargar/xml/", views.descargar_reporte_xml, name="descargar_reporte_xml"),
]
