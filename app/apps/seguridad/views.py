from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpRequest, HttpResponse

def login_view(request: HttpRequest) -> HttpResponse:
    """Handle user login.

    Args:
        request (HttpRequest): The HTTP request object

    Returns:
        HttpResponse: Rendered login page or redirect to home
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')  # Redirect to your home page
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('seguridad:login')