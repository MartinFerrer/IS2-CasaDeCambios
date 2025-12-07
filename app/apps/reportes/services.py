"""Servicios para generar reportes de transacciones - VERSION CORREGIDA"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone


class ReporteTransaccionesService:
    """Servicio para generar reportes de transacciones para usuarios"""

    def __init__(self, cliente_id: int):
        self.cliente_id = cliente_id

        # Importar modelos aquí para evitar import circular
        from apps.transacciones.models import Transaccion
        from apps.usuarios.models import Cliente

        self.Transaccion = Transaccion
        self.Cliente = Cliente

    def generar_reporte(self, fecha_inicio: date, fecha_fin: date, estados: list[str] = None) -> dict[str, Any]:
        """Genera un reporte completo de transacciones para un cliente"""
        # Por defecto incluir todos los estados
        if estados is None or len(estados) == 0:
            estados = ["completada", "pendiente", "cancelada", "rechazada"]

        print(f"🔍 DEBUG: Iniciando reporte para cliente {self.cliente_id}")
        print(f"🔍 DEBUG: Fechas {fecha_inicio} a {fecha_fin}")
        print(f"🔍 DEBUG: Estados {estados}")

        # Obtener cliente
        try:
            cliente = self.Cliente.objects.get(id=self.cliente_id)
            print(f"✅ DEBUG: Cliente encontrado: {cliente.nombre}")
        except self.Cliente.DoesNotExist:
            print(f"❌ DEBUG: Cliente {self.cliente_id} no encontrado")
            raise ValueError(f"Cliente con ID {self.cliente_id} no encontrado")

        # Filtrar transacciones
        transacciones_qs = self._filtrar_transacciones(fecha_inicio, fecha_fin, estados)
        total_transacciones = transacciones_qs.count()
        print(f"🔍 DEBUG: Transacciones encontradas: {total_transacciones}")

        # Calcular estadísticas SIMPLIFICADAS (sin comisiones)
        estadisticas = self._calcular_estadisticas_simple(transacciones_qs)
        print("✅ DEBUG: Estadísticas calculadas")

        # Obtener detalles SIMPLIFICADOS (sin comisiones)
        transacciones_detalle = self._obtener_transacciones_simple(transacciones_qs)
        print(f"✅ DEBUG: Detalles obtenidos: {len(transacciones_detalle)} transacciones")

        # Agregar cálculo de comisiones para cada transacción
        transacciones_detalle_con_comisiones = []
        for transaccion in transacciones_detalle:
            # Importar el módulo de cálculos
            from apps.transacciones.utils import calculos_tasas_comisiones

            try:
                # Calcular comisiones para esta transacción específica
                comision_pago = calculos_tasas_comisiones.obtener_comision_medio_completa(
                    medio=transaccion["metodo_pago"] or "efectivo",
                    cliente=cliente,
                    tipo_operacion=transaccion["tipo_operacion"],
                    es_pago=True,
                )

                comision_cobro = calculos_tasas_comisiones.obtener_comision_medio_completa(
                    medio=transaccion["medio_cobro"] or "efectivo",
                    cliente=cliente,
                    tipo_operacion=transaccion["tipo_operacion"],
                    es_pago=False,
                )

                # Comisión total
                comision_total = comision_pago + comision_cobro

                # Si es Stripe, agregar comisión fija
                if transaccion["metodo_pago"] == "stripe_new" or (
                    transaccion["metodo_pago"] and transaccion["metodo_pago"].startswith("stripe_")
                ):
                    comision_stripe = calculos_tasas_comisiones.obtener_comision_fija_stripe_pyg()
                    comision_total += comision_stripe

            except Exception:
                # Si falla el cálculo, usar 0
                comision_pago = Decimal("0")
                comision_cobro = Decimal("0")
                comision_total = Decimal("0")

            transaccion_data = {
                **transaccion,
                "comision_pago": float(comision_pago),
                "comision_cobro": float(comision_cobro),
                "comision_total": float(comision_total),
                "comision_porcentaje": float((comision_total / transaccion["monto_origen"]) * 100)
                if transaccion["monto_origen"] > 0
                else 0,
            }

            transacciones_detalle_con_comisiones.append(transaccion_data)

        total_comisiones = sum(t["comision_total"] for t in transacciones_detalle_con_comisiones)
        promedio_comisiones = (
            total_comisiones / len(transacciones_detalle_con_comisiones) if transacciones_detalle_con_comisiones else 0
        )

        estadisticas["totales"]["comisiones"] = total_comisiones
        estadisticas["promedios"]["comision"] = promedio_comisiones

        reporte = {
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "ruc": cliente.ruc,
                "email": cliente.email or "No especificado",
            },
            "periodo": {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "estados_incluidos": estados,
            },
            "estadisticas_generales": estadisticas,
            "agrupacion_por_tipo": self._agrupar_por_tipo_simple(transacciones_qs),
            "agrupacion_por_divisa": self._agrupar_por_divisa_simple(transacciones_qs),
            "agrupacion_por_estado": self._agrupar_por_estado_simple(transacciones_qs),
            "transacciones_detalle": transacciones_detalle_con_comisiones,
            "metadatos": {
                "fecha_generacion": timezone.now(),
                "total_registros": total_transacciones,
            },
        }

        return reporte

    def _filtrar_transacciones(self, fecha_inicio: date, fecha_fin: date, estados: list[str]):
        """Filtra transacciones por cliente, fechas y estados"""
        queryset = self.Transaccion.objects.filter(
            cliente_id=self.cliente_id,
            fecha_creacion__date__gte=fecha_inicio,
            fecha_creacion__date__lte=fecha_fin,
            estado__in=estados,
        ).select_related("divisa_origen", "divisa_destino")

        print(f"🔍 DEBUG: Query SQL: {queryset.query}")
        return queryset

    def _calcular_estadisticas_simple(self, queryset):
        """Calcula estadísticas generales SIN comisiones"""
        total_transacciones = queryset.count()

        if total_transacciones == 0:
            return {
                "totales": {
                    "transacciones": 0,
                    "monto_origen": Decimal("0"),
                    "monto_destino": Decimal("0"),
                    "comisiones": Decimal("0"),
                },
                "promedios": {
                    "monto_origen": Decimal("0"),
                    "monto_destino": Decimal("0"),
                    "comision": Decimal("0"),
                },
            }

        agregaciones = queryset.aggregate(
            total_monto_origen=Sum("monto_origen"),
            total_monto_destino=Sum("monto_destino"),
        )

        monto_origen_total = agregaciones["total_monto_origen"] or Decimal("0")
        monto_destino_total = agregaciones["total_monto_destino"] or Decimal("0")

        return {
            "totales": {
                "transacciones": total_transacciones,
                "monto_origen": monto_origen_total,
                "monto_destino": monto_destino_total,
                "comisiones": Decimal("0"),
            },
            "promedios": {
                "monto_origen": monto_origen_total / total_transacciones if total_transacciones > 0 else Decimal("0"),
                "monto_destino": monto_destino_total / total_transacciones if total_transacciones > 0 else Decimal("0"),
                "comision": Decimal("0"),
            },
        }

    def _obtener_transacciones_simple(self, queryset):
        """Obtiene las transacciones SIN calcular comisiones"""
        transacciones = []

        for transaccion in queryset:
            transacciones.append(
                {
                    "id_transaccion": transaccion.id_transaccion,
                    "tipo_operacion": transaccion.tipo_operacion,
                    "estado": transaccion.estado,
                    "monto_origen": transaccion.monto_origen,
                    "monto_destino": transaccion.monto_destino,
                    "comision_aplicada": Decimal("0"),
                    "fecha_creacion": transaccion.fecha_creacion,
                    "fecha_actualizacion": transaccion.fecha_actualizacion,
                    "divisa_origen__codigo": transaccion.divisa_origen.codigo if transaccion.divisa_origen else "N/A",
                    "divisa_destino__codigo": transaccion.divisa_destino.codigo
                    if transaccion.divisa_destino
                    else "N/A",
                    "metodo_pago": getattr(
                        transaccion, "metodo_pago", getattr(transaccion, "medio_pago", "No especificado")
                    ),
                    "medio_cobro": getattr(transaccion, "medio_cobro", "No especificado"),
                }
            )

        return transacciones

    def _agrupar_por_tipo_simple(self, queryset):
        """Agrupa las transacciones por tipo de operación SIN comisiones"""
        tipos = {}

        for tipo in ["compra", "venta"]:
            tipo_qs = queryset.filter(tipo_operacion=tipo)

            if tipo_qs.exists():
                agregaciones = tipo_qs.aggregate(
                    count=Count("id_transaccion"),
                    total_monto_origen=Sum("monto_origen"),
                    total_monto_destino=Sum("monto_destino"),
                )

                tipos[tipo] = {
                    "cantidad": agregaciones["count"],
                    "monto_origen_total": agregaciones["total_monto_origen"] or Decimal("0"),
                    "monto_destino_total": agregaciones["total_monto_destino"] or Decimal("0"),
                    "comisiones_total": Decimal("0"),
                }

        return tipos

    def _agrupar_por_divisa_simple(self, queryset):
        """Agrupa las transacciones por divisa de origen SIN comisiones"""
        divisas = {}

        divisas_unicas = queryset.values_list("divisa_origen__codigo", flat=True).distinct()

        for divisa_codigo in divisas_unicas:
            if divisa_codigo:
                divisa_qs = queryset.filter(divisa_origen__codigo=divisa_codigo)

                agregaciones = divisa_qs.aggregate(
                    count=Count("id_transaccion"),
                    total_monto_origen=Sum("monto_origen"),
                    total_monto_destino=Sum("monto_destino"),
                )

                divisas[divisa_codigo] = {
                    "cantidad": agregaciones["count"],
                    "monto_origen_total": agregaciones["total_monto_origen"] or Decimal("0"),
                    "monto_destino_total": agregaciones["total_monto_destino"] or Decimal("0"),
                    "comisiones_total": Decimal("0"),
                }

        return divisas

    def _agrupar_por_estado_simple(self, queryset):
        """Agrupa las transacciones por estado SIN comisiones"""
        estados = {}
        total_transacciones = queryset.count()

        for estado in ["completada", "pendiente", "cancelada", "rechazada"]:
            estado_qs = queryset.filter(estado=estado)
            count = estado_qs.count()

            if count > 0:
                agregaciones = estado_qs.aggregate(
                    total_monto_origen=Sum("monto_origen"),
                    total_monto_destino=Sum("monto_destino"),
                )

                estados[estado] = {
                    "cantidad": count,
                    "monto_origen_total": agregaciones["total_monto_origen"] or Decimal("0"),
                    "monto_destino_total": agregaciones["total_monto_destino"] or Decimal("0"),
                    "comisiones_total": Decimal("0"),
                    "porcentaje": round((count / total_transacciones) * 100, 1) if total_transacciones > 0 else 0,
                }

        return estados


class ExportadorReportes:
    """Clase para exportar reportes en diferentes formatos"""

    @staticmethod
    def exportar_a_xml(reporte_data: dict[str, Any]) -> str:
        """Exporta el reporte a formato XML"""
        import xml.etree.ElementTree as ET

        root = ET.Element("reporte_transacciones")

        cliente_elem = ET.SubElement(root, "cliente")
        for key, value in reporte_data["cliente"].items():
            elem = ET.SubElement(cliente_elem, key)
            elem.text = str(value)

        periodo_elem = ET.SubElement(root, "periodo")
        for key, value in reporte_data["periodo"].items():
            elem = ET.SubElement(periodo_elem, key)
            elem.text = str(value)

        stats_elem = ET.SubElement(root, "estadisticas_generales")

        totales_elem = ET.SubElement(stats_elem, "totales")
        for key, value in reporte_data["estadisticas_generales"]["totales"].items():
            elem = ET.SubElement(totales_elem, key)
            elem.text = str(value)

        transacciones_elem = ET.SubElement(root, "transacciones")
        for transaccion in reporte_data["transacciones_detalle"]:
            trans_elem = ET.SubElement(transacciones_elem, "transaccion")
            for key, value in transaccion.items():
                elem = ET.SubElement(trans_elem, key)
                elem.text = str(value) if value is not None else ""

        return ET.tostring(root, encoding="unicode", method="xml")
