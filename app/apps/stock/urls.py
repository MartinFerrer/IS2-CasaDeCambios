"""URLs para la aplicación stock."""

from django.urls import path

from .api_views import (
                        api_denominaciones_divisa,
                        depositar_divisas_api,
                        extraer_divisas_api,
                        obtener_denominaciones_api,
                        obtener_divisas_api,
                        obtener_divisas_con_stock_api,
                        obtener_stock_api,
)

app_name = 'stock'

urlpatterns = [
    # APIs para gestión de stock
    path('api/stock/<int:tauser_id>/', obtener_stock_api, name='stock_api'),
    path('api/divisas/', obtener_divisas_api, name='divisas_api'),
    path('api/divisas-con-stock/<int:tauser_id>/', obtener_divisas_con_stock_api, name='divisas_con_stock_api'),
    path('api/denominaciones/<int:tauser_id>/<str:divisa_id>/', obtener_denominaciones_api, name='denominaciones_api'),
    path('api/denominaciones-divisa/<str:divisa_codigo>/', api_denominaciones_divisa, name='denominaciones_divisa_api'),
    path('api/depositar/', depositar_divisas_api, name='depositar_api'),
    path('api/extraer/', extraer_divisas_api, name='extraer_api'),
]
