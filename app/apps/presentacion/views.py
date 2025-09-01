from django.shortcuts import render


def home(request):
    """Vista para la página de inicio."""
    # Aquí podrías pasar datos como las tasas de cambio
    # tasas_de_cambio = get_tasas_de_cambio()
    # return render(request, 'index.html', {'tasas': tasas_de_cambio})
    return render(request, "index.html")
