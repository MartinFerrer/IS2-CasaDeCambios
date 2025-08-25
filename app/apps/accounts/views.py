def home(request):
    return render(request, 'accounts/home.html')

from .forms import CustomUserCreationForm
from django.shortcuts import render, redirect
from django.contrib import messages

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada correctamente!')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

