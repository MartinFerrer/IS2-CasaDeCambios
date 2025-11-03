.. _presentacion-doc:

Presentación App
================

Descripción General
-------------------

Este módulo maneja la presentación de tasas de cambio y visualización de historiales
para los usuarios del sistema. Incluye funcionalidades de frontend para mostrar
tasas actuales y gráficos históricos interactivos usando Plotly.js.

Vistas y Templates
------------------

Vista Principal (index.html)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

La vista principal muestra las tasas de cambio actuales y proporciona acceso
al historial gráfico de las mismas.

**Componentes incluidos:**

- ``tasas_actuales.html``: Vista de tabla con tasas actuales
- ``historial_tasas.html``: Vista de gráfico de historial

**Gestor JavaScript:** ``TasasManager``

Clase principal que gestiona:

- Carga de tasas actuales desde el API
- Visualización de historial gráfico usando Plotly.js
- Filtrado de datos por período (7, 30, 90, 180, 365 días)
- Agrupamiento de datos según el período seleccionado
- Cálculo y visualización de tendencias de precios

Estrategias de Agrupamiento por Período
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **7 días**: Muestra cada día individualmente
- **30 días**: Muestra cada día individualmente
- **90 días**: Agrupa cada 3 días
- **180 días (6 meses)**: Agrupa por mes
- **365 días (1 año)**: Agrupa por mes

Integración con Backend
------------------------

**Endpoint API:** ``operaciones:tasas_cambio_api``

**Método:** GET

**Auto-refresh:** Cada 30 segundos (solo en vista de tasas actuales)

Dependencias
------------

- **Plotly.js**: Librería de visualización de gráficos (CDN)

Módulos de Python
-----------------

.. automodule:: apps.presentacion.models
   :members:

.. automodule:: apps.presentacion.views
   :members:

.. automodule:: apps.presentacion.urls
   :members:

