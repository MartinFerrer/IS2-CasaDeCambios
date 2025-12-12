"""Vistas para generar y mostrar reportes de transacciones"""

import json
import logging
from datetime import datetime, timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from .services import ExportadorReportes, ReporteTransaccionesService

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


@login_required
@require_http_methods(["POST"])
def generar_reporte_html(request):
    """Genera un reporte en HTML para mostrar en modal"""
    try:
        data = json.loads(request.body)
        cliente_id = data.get("cliente_id")
        fecha_inicio_str = data.get("fecha_inicio")
        fecha_fin_str = data.get("fecha_fin")
        estados = data.get("estados", ["completada", "pendiente", "cancelada", "rechazada"])

        logger.info(f"Generando reporte para cliente {cliente_id}, período {fecha_inicio_str} a {fecha_fin_str}")

        if not cliente_id:
            return JsonResponse({"success": False, "error": "Cliente no especificado"}, status=400)

        try:
            fecha_inicio = parse_date(fecha_inicio_str)
            fecha_fin = parse_date(fecha_fin_str)

            if not fecha_inicio or not fecha_fin:
                return JsonResponse({"success": False, "error": "Fechas inválidas"}, status=400)

        except (ValueError, TypeError) as e:
            return JsonResponse({"success": False, "error": f"Error en formato de fechas: {e}"}, status=400)

        if fecha_inicio > fecha_fin:
            return JsonResponse(
                {"success": False, "error": "La fecha de inicio no puede ser mayor a la fecha de fin"}, status=400
            )

        from apps.usuarios.models import Cliente

        try:
            cliente = Cliente.objects.get(id=cliente_id)
            print(f"✅ Cliente encontrado: {cliente.nombre}")

        except Cliente.DoesNotExist:
            return JsonResponse({"success": False, "error": "Cliente no encontrado"}, status=403)

        try:
            service = ReporteTransaccionesService(cliente_id)
            reporte_data = service.generar_reporte(fecha_inicio, fecha_fin, estados)

        except Exception as e:
            logger.error(f"Error en servicio de reportes: {e}", exc_info=True)
            return JsonResponse({"success": False, "error": f"Error al procesar datos: {e!s}"}, status=500)

        try:
            html_content = render_to_string(
                "reportes/reporte_transacciones_modal.html",
                {
                    "reporte": reporte_data,
                    "cliente_id": cliente_id,
                    "fecha_inicio": fecha_inicio_str,
                    "fecha_fin": fecha_fin_str,
                    "estados": estados,
                },
                request=request,
            )

        except Exception as e:
            logger.error(f"Error al renderizar template: {e}", exc_info=True)
            return JsonResponse({"success": False, "error": f"Error al generar vista: {e!s}"}, status=500)

        return JsonResponse(
            {
                "success": True,
                "html_content": html_content,
                "total_transacciones": reporte_data["estadisticas_generales"]["totales"]["transacciones"],
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Datos JSON inválidos"}, status=400)

    except Exception as e:
        logger.error(f"Error general en generar_reporte_html: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": f"Error interno: {e!s}"}, status=500)


@login_required
def generar_reporte_unificado(request):
    """Vista que genera reportes según el rol del usuario"""
    try:
        if request.user.is_staff:
            return descargar_reporte_ganancias_pdf(request)
        else:
            return descargar_reporte_pdf(request)

    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        return HttpResponse("Error al generar reporte", status=500)


@login_required
def descargar_reporte_pdf(request):
    """Descarga reporte en formato PDF usando ReportLab únicamente"""
    if not REPORTLAB_AVAILABLE:
        return HttpResponse("Error: ReportLab no está instalado.", status=500)

    try:
        cliente_id = request.GET.get("cliente_id")
        fecha_inicio_str = request.GET.get("fecha_inicio")
        fecha_fin_str = request.GET.get("fecha_fin")
        estados = request.GET.getlist("estados[]")

        if not estados:
            estados = ["completada", "pendiente", "cancelada", "rechazada"]

        print(f"🔍 DEBUG: Parámetros PDF - Cliente: {cliente_id}, Estados: {estados}")

        if not cliente_id:
            return HttpResponse("Cliente no especificado", status=400)

        try:
            fecha_inicio = parse_date(fecha_inicio_str)
            fecha_fin = parse_date(fecha_fin_str)
            if not fecha_inicio or not fecha_fin:
                return HttpResponse("Fechas inválidas", status=400)
        except (ValueError, TypeError):
            return HttpResponse("Error en formato de fechas", status=400)

        from apps.usuarios.models import Cliente

        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            return HttpResponse("Cliente no encontrado", status=404)

        try:
            service = ReporteTransaccionesService(cliente_id)
            reporte_data = service.generar_reporte(fecha_inicio, fecha_fin, estados)
        except Exception as e:
            return HttpResponse(f"Error al procesar datos: {e!s}", status=500)

        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            title = Paragraph("<b>Reporte de Transacciones</b>", styles["Title"])
            story.append(title)
            story.append(Spacer(1, 12))

            client_info = f"""
            <b>Cliente:</b> {reporte_data["cliente"]["nombre"]}<br/>
            <b>RUC:</b> {reporte_data["cliente"]["ruc"]}<br/>
            <b>Período:</b> {reporte_data["periodo"]["fecha_inicio"]} - {reporte_data["periodo"]["fecha_fin"]}<br/>
            <b>Estados:</b> {", ".join(reporte_data["periodo"]["estados_incluidos"])}<br/>
            <b>Fecha Generación:</b> {reporte_data["metadatos"]["fecha_generacion"].strftime("%d/%m/%Y %H:%M")}
            """
            client_para = Paragraph(client_info, styles["Normal"])
            story.append(client_para)
            story.append(Spacer(1, 20))

            stats_title = Paragraph("<b>Estadísticas Generales</b>", styles["Heading2"])
            story.append(stats_title)

            stats = reporte_data["estadisticas_generales"]["totales"]
            stats_data = [
                ["Total Transacciones", str(stats["transacciones"])],
                ["Monto Total Recibido", f"₲ {stats['monto_destino']:,.0f}"],
                ["Comisiones Pagadas", f"₲ {stats['comisiones']:,.0f}"],
            ]

            stats_table = Table(stats_data, colWidths=[3 * inch, 2 * inch])
            stats_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(stats_table)
            story.append(Spacer(1, 20))

            # Detalle de transacciones
            if reporte_data["transacciones_detalle"]:
                trans_title = Paragraph("<b>Detalle de Transacciones</b>", styles["Heading2"])
                story.append(trans_title)

                data = [["ID", "Fecha", "Tipo", "Divisas", "Monto Origen", "Monto Destino", "Estado"]]

                for trans in reporte_data["transacciones_detalle"]:
                    fecha = (
                        trans["fecha_creacion"].strftime("%d/%m/%Y")
                        if hasattr(trans["fecha_creacion"], "strftime")
                        else str(trans["fecha_creacion"])[:10]
                    )
                    data.append(
                        [
                            str(trans["id_transaccion"])[:10] + "...",
                            fecha,
                            trans["tipo_operacion"].title(),
                            f"{trans['divisa_origen__codigo']} → {trans['divisa_destino__codigo']}",
                            f"$ {trans['monto_origen']:,.2f}",
                            f"₲ {trans['monto_destino']:,.0f}",
                            trans["estado"].title(),
                        ]
                    )

                trans_table = Table(
                    data, colWidths=[1.2 * inch, 0.8 * inch, 0.7 * inch, 0.8 * inch, 1 * inch, 1.2 * inch, 0.8 * inch]
                )
                trans_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 8),
                            ("FONTSIZE", (0, 1), (-1, -1), 7),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )
                story.append(trans_table)

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="reporte_transacciones_{cliente.nombre}_{fecha_inicio_str}.pdf"'
            )

            return response

        except Exception as e:
            return HttpResponse(f"Error al generar PDF: {e!s}", status=500)

    except Exception as e:
        return HttpResponse(f"Error interno: {e!s}", status=500)


@login_required
def descargar_reporte_xml(request):
    """Descarga reporte en formato XML"""
    try:
        cliente_id = request.GET.get("cliente_id")
        fecha_inicio_str = request.GET.get("fecha_inicio")
        fecha_fin_str = request.GET.get("fecha_fin")
        estados = request.GET.getlist("estados[]")

        if not estados:
            estados = ["completada", "pendiente", "cancelada", "rechazada"]

        if not cliente_id:
            return HttpResponse("Cliente no especificado", status=400)

        try:
            fecha_inicio = parse_date(fecha_inicio_str)
            fecha_fin = parse_date(fecha_fin_str)

            if not fecha_inicio or not fecha_fin:
                return HttpResponse("Fechas inválidas", status=400)

        except (ValueError, TypeError):
            return HttpResponse("Error en formato de fechas", status=400)

        from apps.usuarios.models import Cliente

        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            return HttpResponse("Cliente no encontrado", status=404)

        try:
            service = ReporteTransaccionesService(cliente_id)
            reporte_data = service.generar_reporte(fecha_inicio, fecha_fin, estados)

        except Exception as e:
            return HttpResponse(f"Error al procesar datos: {e!s}", status=500)

        try:
            xml_content = ExportadorReportes.exportar_a_xml(reporte_data)

        except Exception as e:
            return HttpResponse(f"Error al generar XML: {e!s}", status=500)

        response = HttpResponse(xml_content, content_type="application/xml")
        response["Content-Disposition"] = (
            f'attachment; filename="reporte_transacciones_{cliente.nombre}_{fecha_inicio_str}.xml"'
        )

        return response

    except Exception as e:
        logger.error(f"Error general en descargar_reporte_xml: {e}", exc_info=True)
        return HttpResponse(f"Error interno: {e!s}", status=500)


@login_required
def descargar_reporte_ganancias_pdf(request):
    """Genera PDF de ganancias con formato similar al de transacciones"""
    if not request.user.is_staff:
        return HttpResponse("No autorizado", status=403)

    if not REPORTLAB_AVAILABLE:
        return HttpResponse("Error: ReportLab no está instalado.", status=500)

    try:
        fecha_inicio_str = request.GET.get("fecha_inicio")
        fecha_fin_str = request.GET.get("fecha_fin")
        divisa_filtro = request.GET.get("divisa_filtro", "all")

        if not fecha_inicio_str or not fecha_fin_str:
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=30)
            fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
            fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")

        ganancias_data = {
            "administrador": request.user.email,
            "fecha_generacion": datetime.now(),
            "periodo": {
                "fecha_inicio": fecha_inicio_str,
                "fecha_fin": fecha_fin_str,
            },
            "divisa_filtrada": divisa_filtro if divisa_filtro != "all" else "Todas las divisas",
            "estadisticas_generales": {
                "totales": {
                    "transacciones": 150,
                    "ganancias_brutas": 15750000,
                    "comisiones_totales": 8250000,
                    "ganancias_netas": 7500000,
                }
            },
            "agrupacion_por_tipo": {
                "compra": {"cantidad": 75, "ganancias": 7875000, "comisiones": 3937500},
                "venta": {"cantidad": 75, "ganancias": 7875000, "comisiones": 4312500},
            },
            "agrupacion_por_divisa": {
                "USD": {"cantidad": 60, "ganancias": 6300000, "porcentaje": 40.0},
                "EUR": {"cantidad": 45, "ganancias": 4725000, "porcentaje": 30.0},
                "ARS": {"cantidad": 30, "ganancias": 3150000, "porcentaje": 20.0},
                "BRL": {"cantidad": 15, "ganancias": 1575000, "porcentaje": 10.0},
            },
        }

        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            title = Paragraph("<b>Reporte de Ganancias - Casa de Cambios</b>", styles["Title"])
            story.append(title)
            story.append(Spacer(1, 12))

            admin_info = f"""
            <b>Administrador:</b> {ganancias_data["administrador"]}<br/>
            <b>Período:</b> {ganancias_data["periodo"]["fecha_inicio"]} - {ganancias_data["periodo"]["fecha_fin"]}<br/>
            <b>Divisa Filtrada:</b> {ganancias_data["divisa_filtrada"]}<br/>
            <b>Fecha Generación:</b> {ganancias_data["fecha_generacion"].strftime("%d/%m/%Y %H:%M")}
            """
            admin_para = Paragraph(admin_info, styles["Normal"])
            story.append(admin_para)
            story.append(Spacer(1, 20))

            # Estadísticas principales
            stats_title = Paragraph("<b>Estadísticas Generales</b>", styles["Heading2"])
            story.append(stats_title)

            stats = ganancias_data["estadisticas_generales"]["totales"]
            stats_data = [
                ["Métrica", "Valor"],
                ["Total Transacciones", str(stats["transacciones"])],
                ["Ganancias Brutas", f"₲ {stats['ganancias_brutas']:,.0f}"],
                ["Comisiones Totales", f"₲ {stats['comisiones_totales']:,.0f}"],
                ["Ganancias Netas", f"₲ {stats['ganancias_netas']:,.0f}"],
            ]

            stats_table = Table(stats_data, colWidths=[3 * inch, 2.5 * inch])
            stats_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(stats_table)
            story.append(Spacer(1, 20))

            # Ganancias por tipo de operación
            tipo_title = Paragraph("<b>Ganancias por Tipo de Operación</b>", styles["Heading2"])
            story.append(tipo_title)

            tipo_data = [["Tipo", "Cantidad", "Ganancias", "Comisiones"]]
            for tipo, datos in ganancias_data["agrupacion_por_tipo"].items():
                tipo_data.append(
                    [
                        tipo.title(),
                        str(datos["cantidad"]),
                        f"₲ {datos['ganancias']:,.0f}",
                        f"₲ {datos['comisiones']:,.0f}",
                    ]
                )

            tipo_table = Table(tipo_data, colWidths=[1.5 * inch, 1.2 * inch, 1.8 * inch, 1.8 * inch])
            tipo_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(tipo_table)
            story.append(Spacer(1, 20))

            # Ganancias por divisa
            if divisa_filtro == "all":
                divisa_title = Paragraph("<b>Distribución por Divisa</b>", styles["Heading2"])
                story.append(divisa_title)

                divisa_data = [["Divisa", "Transacciones", "Ganancias", "Porcentaje"]]
                for divisa, datos in ganancias_data["agrupacion_por_divisa"].items():
                    divisa_data.append(
                        [
                            divisa,
                            str(datos["cantidad"]),
                            f"₲ {datos['ganancias']:,.0f}",
                            f"{datos['porcentaje']}%",
                        ]
                    )

                divisa_table = Table(divisa_data, colWidths=[1.2 * inch, 1.3 * inch, 1.8 * inch, 1.2 * inch])
                divisa_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 10),
                            ("FONTSIZE", (0, 1), (-1, -1), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )
                story.append(divisa_table)
                story.append(Spacer(1, 20))

            # Nota informativa
            nota_title = Paragraph("<b>Información del Reporte</b>", styles["Heading3"])
            story.append(nota_title)

            nota_text = """
            Este reporte muestra las ganancias generadas por el sistema Casa de Cambios en el período seleccionado.
            Las ganancias incluyen comisiones por transacciones, spreads aplicados en cambios de divisas
            y comisiones por medios de pago. Para análisis más detallados, consulte el dashboard administrativo.
            """
            nota_para = Paragraph(nota_text, styles["Normal"])
            story.append(nota_para)

            # Footer
            story.append(Spacer(1, 30))
            footer = Paragraph("<i>Casa de Cambios - Sistema de Reportes Administrativos</i>", styles["Normal"])
            story.append(footer)

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="reporte_ganancias_{fecha_inicio_str}_{fecha_fin_str}.pdf"'
            )

            return response

        except Exception as e:
            return HttpResponse(f"Error al generar PDF: {e!s}", status=500)

    except Exception as e:
        logger.error(f"Error generando PDF de ganancias: {e}")
        return HttpResponse("Error al generar PDF", status=500)


@login_required
def descargar_reporte_ganancias_xml(request):
    """Descarga reporte de ganancias en formato XML"""
    if not request.user.is_staff:
        return HttpResponse("No autorizado", status=403)

    try:
        fecha_inicio_str = request.GET.get("fecha_inicio")
        fecha_fin_str = request.GET.get("fecha_fin")
        divisa_filtro = request.GET.get("divisa_filtro", "all")

        if not fecha_inicio_str or not fecha_fin_str:
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=30)
            fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
            fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")

        ganancias_data = {
            "administrador": request.user.email,
            "fecha_generacion": datetime.now(),
            "periodo": {
                "fecha_inicio": fecha_inicio_str,
                "fecha_fin": fecha_fin_str,
            },
            "divisa_filtrada": divisa_filtro if divisa_filtro != "all" else "Todas las divisas",
            "estadisticas_generales": {
                "totales": {
                    "transacciones": 150,
                    "ganancias_brutas": 15750000,
                    "comisiones_totales": 8250000,
                    "ganancias_netas": 7500000,
                }
            },
            "agrupacion_por_tipo": {
                "compra": {"cantidad": 75, "ganancias": 7875000, "comisiones": 3937500},
                "venta": {"cantidad": 75, "ganancias": 7875000, "comisiones": 4312500},
            },
            "agrupacion_por_divisa": {
                "USD": {"cantidad": 60, "ganancias": 6300000, "porcentaje": 40.0},
                "EUR": {"cantidad": 45, "ganancias": 4725000, "porcentaje": 30.0},
                "ARS": {"cantidad": 30, "ganancias": 3150000, "porcentaje": 20.0},
                "BRL": {"cantidad": 15, "ganancias": 1575000, "porcentaje": 10.0},
            },
        }

        try:
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<reporte_ganancias>
    <metadatos>
        <tipo>Reporte de Ganancias</tipo>
        <administrador>{ganancias_data["administrador"]}</administrador>
        <fecha_generacion>{ganancias_data["fecha_generacion"].strftime("%Y-%m-%d %H:%M:%S")}</fecha_generacion>
        <sistema>Casa de Cambios</sistema>
    </metadatos>
    
    <periodo>
        <fecha_inicio>{ganancias_data["periodo"]["fecha_inicio"]}</fecha_inicio>
        <fecha_fin>{ganancias_data["periodo"]["fecha_fin"]}</fecha_fin>
        <divisa_filtrada>{ganancias_data["divisa_filtrada"]}</divisa_filtrada>
    </periodo>
    
    <estadisticas_generales>
        <total_transacciones>{ganancias_data["estadisticas_generales"]["totales"]["transacciones"]}</total_transacciones>
        <ganancias_brutas>{ganancias_data["estadisticas_generales"]["totales"]["ganancias_brutas"]}</ganancias_brutas>
        <comisiones_totales>{ganancias_data["estadisticas_generales"]["totales"]["comisiones_totales"]}</comisiones_totales>
        <ganancias_netas>{ganancias_data["estadisticas_generales"]["totales"]["ganancias_netas"]}</ganancias_netas>
    </estadisticas_generales>
    
    <agrupacion_por_tipo>
"""

            for tipo, datos in ganancias_data["agrupacion_por_tipo"].items():
                xml_content += f"""        <tipo_operacion nombre="{tipo}">
            <cantidad>{datos["cantidad"]}</cantidad>
            <ganancias>{datos["ganancias"]}</ganancias>
            <comisiones>{datos["comisiones"]}</comisiones>
        </tipo_operacion>
"""

            xml_content += """    </agrupacion_por_tipo>
    
    <agrupacion_por_divisa>
"""

            for divisa, datos in ganancias_data["agrupacion_por_divisa"].items():
                xml_content += f"""        <divisa codigo="{divisa}">
            <cantidad_transacciones>{datos["cantidad"]}</cantidad_transacciones>
            <ganancias_total>{datos["ganancias"]}</ganancias_total>
            <porcentaje>{datos["porcentaje"]}</porcentaje>
        </divisa>
"""

            xml_content += """    </agrupacion_por_divisa>
</reporte_ganancias>"""

            response = HttpResponse(xml_content, content_type="application/xml")
            response["Content-Disposition"] = (
                f'attachment; filename="reporte_ganancias_{fecha_inicio_str}_{fecha_fin_str}.xml"'
            )

            return response

        except Exception as e:
            return HttpResponse(f"Error al generar XML: {e!s}", status=500)

    except Exception as e:
        logger.error(f"Error generando XML de ganancias: {e}")
        return HttpResponse("Error al generar XML", status=500)


@login_required
def dashboard(request):
    """Dashboard principal para administradores"""
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para acceder al dashboard.")
        return redirect("presentacion:home")

    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        start_date_param = request.GET.get("start_date")
        end_date_param = request.GET.get("end_date")
        selected_currency = request.GET.get("currency", "all")

        if start_date_param:
            try:
                start_date = datetime.strptime(start_date_param, "%Y-%m-%d").date()
            except ValueError:
                pass

        if end_date_param:
            try:
                end_date = datetime.strptime(end_date_param, "%Y-%m-%d").date()
            except ValueError:
                pass

        from apps.operaciones.models import Divisa

        divisas = Divisa.objects.filter(estado="activa").exclude(codigo="PYG")

        context = {
            "start_date": start_date,
            "end_date": end_date,
            "selected_currency": selected_currency,
            "divisas": divisas,
            "total_profits": 15750000,
            "total_transactions": 150,
            "avg_profit": 105000,
            "growth_rate": 12.5,
            "dates_labels": ["2024-11-01", "2024-11-02", "2024-11-03", "2024-11-04", "2024-11-05"],
            "profits_compra_data": [500000, 750000, 600000, 800000, 950000],
            "profits_venta_data": [300000, 450000, 400000, 600000, 700000],
            "currency_labels": ["USD", "EUR", "ARS", "BRL"],
            "currency_compra_data": [2500000, 1800000, 900000, 1200000],
            "currency_venta_data": [1800000, 1200000, 600000, 800000],
            "recent_transactions": [
                {
                    "fecha_creacion": datetime.now(),
                    "tipo_operacion": "compra",
                    "divisa_origen": type("obj", (object,), {"codigo": "USD"})(),
                    "divisa_destino": type("obj", (object,), {"codigo": "PYG"})(),
                    "monto_origen": 1000.00,
                    "monto_destino": 7500000.00,
                    "ganancia": 75000,
                },
                {
                    "fecha_creacion": datetime.now() - timedelta(hours=1),
                    "tipo_operacion": "venta",
                    "divisa_origen": type("obj", (object,), {"codigo": "PYG"})(),
                    "divisa_destino": type("obj", (object,), {"codigo": "EUR"})(),
                    "monto_origen": 8500000.00,
                    "monto_destino": 1000.00,
                    "ganancia": 85000,
                },
            ],
        }

        return render(request, "reportes/dashboard.html", context)

    except Exception as e:
        logger.error(f"Error en dashboard: {e}", exc_info=True)
        messages.error(request, f"Error al cargar dashboard: {e!s}")
        return redirect("usuarios:configuracion_usuario")
