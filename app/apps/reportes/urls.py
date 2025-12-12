"""URLs para la app de reportes"""

from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    # Reportes de transacciones (para clientes)
    path("transacciones/generar/", views.generar_reporte_html, name="generar_reporte_html"),
    path("transacciones/descargar/pdf/", views.descargar_reporte_pdf, name="descargar_reporte_pdf"),
    path("transacciones/descargar/xml/", views.descargar_reporte_xml, name="descargar_reporte_xml"),
    # Reportes de ganancias (para administradores)
    path("ganancias/pdf/", views.descargar_reporte_ganancias_pdf, name="descargar_reporte_ganancias_pdf"),
    path("ganancias/xml/", views.descargar_reporte_ganancias_xml, name="descargar_reporte_ganancias_xml"),  # 👈 NUEVO
]
