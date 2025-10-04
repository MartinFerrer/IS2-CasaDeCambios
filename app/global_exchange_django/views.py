"""Vistas personalizadas de error para Global Exchange."""

from django.shortcuts import render


def handler400(request, exception=None):
    """Vista personalizada para error 400 - Bad Request.

    Se activa cuando hay solicitudes malformadas.
    """
    return render(request, '400.html', status=400)


def handler403(request, exception=None):
    """Vista personalizada para error 403 - Forbidden.

    Se activa cuando hay problemas de CSRF o permisos.
    """
    return render(request, '403.html', status=403)


def csrf_failure(request, reason=""):
    """Vista específica para errores CSRF.

    Django llama a esta vista cuando falla la verificación CSRF.
    """
    return render(request, '403.html', {'reason': reason}, status=403)


def handler404(request, exception=None):
    """Vista personalizada para error 404 - Not Found.

    Se activa cuando no se encuentra una página.
    """
    return render(request, '404.html', status=404)


def handler500(request):
    """Vista personalizada para error 500 - Internal Server Error.

    Se activa cuando hay errores del servidor.
    """
    return render(request, '500.html', status=500)
