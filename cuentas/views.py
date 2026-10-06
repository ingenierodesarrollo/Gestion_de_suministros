from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from .models import Rol
from .permisos import rol_requerido


@login_required
def inicio(request):
    return render(request, "inicio.html")


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def zona_admin(request):
    return HttpResponse("Zona solo para administradores.")