from django.shortcuts import render
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomUserCreationForm
from django.shortcuts import render, redirect

def home(request):
    """Home page view"""
    return render(request, 'file_processor/home.html')

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('file_processor:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})