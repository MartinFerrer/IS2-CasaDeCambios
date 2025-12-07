"""Vistas para generar y mostrar reportes de transacciones"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from .services import ExportadorReportes, ReporteTransaccionesService

logger = logging.getLogger(__name__)


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
            html_content = render(
                request,
                "reportes/reporte_transacciones_modal.html",
                {
                    "reporte": reporte_data,
                    "cliente_id": cliente_id,
                    "fecha_inicio": fecha_inicio_str,
                    "fecha_fin": fecha_fin_str,
                    "estados": estados,
                },
            ).content.decode("utf-8")

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
def descargar_reporte_pdf(request):
    """Descarga reporte en formato PDF usando ReportLab únicamente"""
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
            from io import BytesIO

            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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

        except ImportError:
            return HttpResponse("Error: ReportLab no está instalado.", status=500)

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
