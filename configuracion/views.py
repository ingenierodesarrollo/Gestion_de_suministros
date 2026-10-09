from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from areas.models import Area
from cuentas.models import Rol
from cuentas.permisos import rol_requerido

from proyecciones.models import ProductoSugerido, UnidadMedida
from .forms import AreaForm, ProductoForm, UnidadForm



@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def areas_lista(request):
    return render(request, 'configuracion/areas_lista.html', {'areas': Area.objects.all()})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def area_guardar(request, pk=None):
    """Sirve para crear (sin pk) y para editar (con pk)."""
    area = get_object_or_404(Area, pk=pk) if pk else None
    form = AreaForm(request.POST or None, instance=area)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Área guardada.')
        return redirect('configuracion:areas')
    return render(request, 'configuracion/area_form.html', {'form': form, 'area': area})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def area_alternar(request, pk):
    area = get_object_or_404(Area, pk=pk)
    if request.method == 'POST':  # solo con el botón
        area.activa = not area.activa
        area.save()
        messages.success(request, f'{area.nombre}: {"activa" if area.activa else "desactivada"}.')
    return redirect('configuracion:areas')

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def unidades_lista(request):
    return render(request, 'configuracion/unidades_lista.html', {'unidades': UnidadMedida.objects.all()})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def unidad_guardar(request, pk=None):
    unidad = get_object_or_404(UnidadMedida, pk=pk) if pk else None
    form = UnidadForm(request.POST or None, instance=unidad)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Unidad guardada.')
        return redirect('configuracion:unidades')
    titulo = 'Editar unidad de medida' if unidad else 'Nueva unidad de medida'
    return render(request, 'configuracion/form_simple.html', {'form': form, 'titulo': titulo, 'volver': 'configuracion:unidades'})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def productos_lista(request):
    return render(request, 'configuracion/productos_lista.html', {'productos': ProductoSugerido.objects.all()})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def producto_guardar(request, pk=None):
    producto = get_object_or_404(ProductoSugerido, pk=pk) if pk else None
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Producto guardado.')
        return redirect('configuracion:productos')
    titulo = 'Editar producto sugerido' if producto else 'Nuevo producto sugerido'
    return render(request, 'configuracion/form_simple.html', {'form': form, 'titulo': titulo, 'volver': 'configuracion:productos'})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def producto_alternar(request, pk):
    producto = get_object_or_404(ProductoSugerido, pk=pk)
    if request.method == 'POST':  # solo con el botón
        producto.activo = not producto.activo
        producto.save()
        messages.success(request, f'{producto.nombre}: {"activo" if producto.activo else "desactivado"}.')
    return redirect('configuracion:productos')

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def panel(request):
    return render(request, 'configuracion/panel.html')