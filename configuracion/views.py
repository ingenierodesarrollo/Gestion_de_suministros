from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render


from areas.models import Area
from cuentas.models import Rol, Usuario
from cuentas.permisos import rol_requerido

from proyecciones.models import ProductoSugerido, UnidadMedida
from .forms import AreaForm, ProductoForm, UnidadForm, UsuarioCrearForm, UsuarioEditarForm


from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm



@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def areas_lista(request):
    coordinadores = Usuario.objects.filter(
        rol=Rol.COORDINADOR, activo=True,
    ).order_by('nombre', 'correo')
    areas = Area.objects.prefetch_related(
        Prefetch('usuarios', queryset=coordinadores, to_attr='coordinadores_activos')
    )
    return render(request, 'configuracion/areas_lista.html', {'areas': areas})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def area_guardar(request, pk=None):
    """Sirve para crear (sin pk) y para editar (con pk)."""
    area = get_object_or_404(Area, pk=pk) if pk else None
    form = AreaForm(request.POST or None, instance=area)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            area = form.save()
            form.cleaned_data['coordinadores'].update(area=area)
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


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def usuarios_lista(request):
    usuarios = Usuario.objects.select_related('area')
    return render(request, 'configuracion/usuarios_lista.html', {'usuarios': usuarios})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def usuario_crear(request):
    form = UsuarioCrearForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save(commit=False)
        usuario.debe_cambiar_clave = True
        usuario.save()
        messages.success(request, 'Usuario creado.')
        return redirect('configuracion:usuarios')
    return render(request, 'configuracion/form_simple.html', {
        'form': form, 'titulo': 'Nuevo usuario', 'volver': 'configuracion:usuarios'})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    rol_original = usuario.rol
    form = UsuarioEditarForm(request.POST or None, instance=usuario)
    if request.method == 'POST' and form.is_valid():
        datos = form.cleaned_data
        if usuario.pk == request.user.pk and (not datos['activo'] or datos['rol'] != rol_original):
            form.add_error(None, 'No puedes desactivarte ni cambiar tu propio rol.')
        else:
            form.save()
            messages.success(request, 'Usuario guardado.')
            return redirect('configuracion:usuarios')
    return render(request, 'configuracion/form_simple.html', {
        'form': form, 'titulo': 'Editar usuario', 'volver': 'configuracion:usuarios'})


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def usuario_clave(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = SetPasswordForm(usuario, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if usuario.pk == request.user.pk:
            update_session_auth_hash(request, usuario)  # para no cerrarle la sesión a quien se cambia su propia clave
        else:
            usuario.debe_cambiar_clave = True  # la clave la puso otra persona: debe cambiarla al ingresar
            usuario.save(update_fields=['debe_cambiar_clave'])
        messages.success(request, f'Clave nueva guardada para {usuario.nombre}.')
        return redirect('configuracion:usuarios')
    return render(request, 'configuracion/form_simple.html', {
        'form': form, 'titulo': f'Clave nueva para {usuario.nombre}', 'volver': 'configuracion:usuarios'})
    
