import plotly.graph_objects as go
from django.shortcuts import render


def index(request):
    # sample plotly figure rendered server-side
    fig = go.Figure(data=[go.Bar(x=["USD", "EUR", "GBP"], y=[1.0, 0.9, 0.8])])
    graphJSON = fig.to_json()
    return render(request, "index.html", {"graphJSON": graphJSON})
