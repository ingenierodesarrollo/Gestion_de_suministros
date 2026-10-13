from django.shortcuts import get_object_or_404, redirect, render
from cuentas.models import Rol
from cuentas.permisos import rol_requerido
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils import timezone
from datetime import date
from django.urls import reverse
from .consolidado import MESES_CORTOS, consolidado_por_area, consolidado_por_producto
from django.http import HttpResponse
from .exportar import construir_excel

from .models import EstadoPeriodo, EstadoProyeccion, ProductoSugerido, Linea, ProyeccionArea, Periodo, AccionBitacora, Bitacora
from .forms import AutorizadoFormSet ,AbrirPeriodoForm, CorreccionLineaForm,LineaForm
from .servicios import abrir_periodo, guardar_correccion, valores_linea, alternar_periodo, registrar, registrar_cambios, nombre_registro, nombre_campo


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def mi_proyeccion(request):
    """Lista las proyecciones del área del usuario que inició sesión."""
    proyecciones = ProyeccionArea.objects.filter(area=request.user.area).select_related('periodo', 'area')
    return render(request, 'proyecciones/mi_proyeccion.html', {'proyecciones': proyecciones})

@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def detalle_proyeccion(request, pk):
    """Muestra las líneas de una proyección con su total y costo."""
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    # Un coordinador no puede ver proyecciones de otra área cambiando el número en la dirección.
    if request.user.es_coordinador and proyeccion.area_id != request.user.area_id:
        raise PermissionDenied
    lineas = proyeccion.lineas.select_related('unidad')
    costo_total = sum(linea.costo for linea in lineas)
    puede_editar = (proyeccion.estado == EstadoProyeccion.BORRADOR
                    and proyeccion.periodo.estado == EstadoPeriodo.ABIERTO)
    return render(request, 'proyecciones/detalle.html', {
        'proyeccion': proyeccion, 'lineas': lineas, 'costo_total': costo_total, 'puede_editar': puede_editar,
    })
    
def _obtener_proyeccion(request, pk):
    """Trae la proyección y bloquea a un coordinador si no es de su área."""
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    if request.user.es_coordinador and proyeccion.area_id != request.user.area_id:
        raise PermissionDenied
    return proyeccion

def _exigir_periodo_abierto(proyeccion):
    """Con el periodo cerrado, nadie agrega, edita, borra ni envía líneas (se puede reabrir)."""
    if proyeccion.periodo.estado != EstadoPeriodo.ABIERTO:
        raise PermissionDenied

def _nombres_sugeridos():
    """Nombres activos que se ofrecen como sugerencia en el campo producto."""
    return ProductoSugerido.objects.filter(activo=True).values_list('nombre',
flat=True)


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def agregar_linea(request, pk):
    proyeccion = _obtener_proyeccion(request, pk)
    if proyeccion.estado != EstadoProyeccion.BORRADOR:
        raise PermissionDenied  # ya enviada: el área no la cambia
    _exigir_periodo_abierto(proyeccion)
    form = LineaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        linea = form.save(commit=False)  # aún no guarda: falta decirle a qué proyección pertenece
        linea.proyeccion = proyeccion
        linea.save()
        registrar(request.user, AccionBitacora.CREAR, linea, 'producto', None, linea.producto)
        return redirect('proyecciones:detalle', pk=proyeccion.pk)
    return render(request, 'proyecciones/linea_form.html',
                  {'form': form, 'proyeccion': proyeccion, 'titulo': 'Agregar línea',
                   'sugeridos': _nombres_sugeridos()})


def _linea_editable(request, pk):
    """Trae la línea solo si es del área del usuario y la proyección sigue en borrador."""
    linea = get_object_or_404(Linea, pk=pk)
    proyeccion = _obtener_proyeccion(request, linea.proyeccion_id)
    if proyeccion.estado != EstadoProyeccion.BORRADOR:
        raise PermissionDenied
    _exigir_periodo_abierto(proyeccion)
    return linea, proyeccion


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def editar_linea(request, pk):
    linea, proyeccion = _linea_editable(request, pk)
    antes = valores_linea(linea)  # la foto se toma ANTES de crear el formulario
    form = LineaForm(request.POST or None, instance=linea)  # instance = llena el formulario con lo que ya tiene
    if request.method == 'POST' and form.is_valid():
        form.save()
        registrar_cambios(request.user, AccionBitacora.EDITAR, linea, antes)
        return redirect('proyecciones:detalle', pk=proyeccion.pk)
    return render(request, 'proyecciones/linea_form.html',
                  {'form': form, 'proyeccion': proyeccion, 'titulo': 'Editar línea',
                   'sugeridos': _nombres_sugeridos()})


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def borrar_linea(request, pk):
    linea, proyeccion = _linea_editable(request, pk)
    if request.method == 'POST':  # solo borra con el botón, nunca con solo abrir un enlace
        registrar(request.user, AccionBitacora.BORRAR, linea, 'producto', linea.producto, None)
        linea.delete()
    return redirect('proyecciones:detalle', pk=proyeccion.pk)

@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def enviar_proyeccion(request, pk):
    proyeccion = _obtener_proyeccion(request, pk)
    _exigir_periodo_abierto(proyeccion)
    if request.method == 'POST' and proyeccion.estado == EstadoProyeccion.BORRADOR:
        if not proyeccion.lineas.exists():
            messages.error(request, 'Agrega al menos una linea antes de enviar.')
        else:
            proyeccion.estado = EstadoProyeccion.ENVIADA
            proyeccion.fecha_envio = timezone.now()
            proyeccion.save(update_fields=['estado', 'fecha_envio'])
            registrar(request.user, AccionBitacora.ENVIAR, proyeccion, 'estado', EstadoProyeccion.BORRADOR, 
                      EstadoProyeccion.ENVIADA)
            messages.success(request, 'Proyeccion enviada. Ya no se puede modificar')
    return redirect('proyecciones:detalle', pk=proyeccion.pk)

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def revision(request):
    """Todas las proyecciones de todas las áreas, para los administradores."""
    proyecciones = ProyeccionArea.objects.select_related('periodo', 'area')
    return render(request, 'proyecciones/revision.html', {
        'proyecciones': proyecciones, 'periodos': Periodo.objects.all(), 'hoy': date.today(),
    })

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def revisar_proyeccion(request, pk):
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    if proyeccion.estado == EstadoProyeccion.BORRADOR:
        messages.error(request, 'Esa proyección aún no ha sido enviada.')
        return redirect('proyecciones:revision')
    formset = AutorizadoFormSet(request.POST or None, queryset=proyeccion.lineas.select_related('unidad'))
    if request.method == 'POST' and proyeccion.estado == EstadoProyeccion.ENVIADA and formset.is_valid():
        for form in formset:
            if form.has_changed():
                registrar(request.user, AccionBitacora.EDITAR, form.instance, 'cantidad_autorizada',
                          form.initial.get('cantidad_autorizada'), form.cleaned_data['cantidad_autorizada'])
        formset.save()
        messages.success(request, 'Cantidades autorizadas guardadas.')
        return redirect('proyecciones:revisar', pk=proyeccion.pk)
    return render(request, 'proyecciones/revisar.html', {'proyeccion': proyeccion, 'formset': formset})

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def aprobar_proyeccion(request, pk):
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    if request.method == 'POST' and proyeccion.estado == EstadoProyeccion.ENVIADA:
        if proyeccion.lineas.filter(cantidad_autorizada__isnull=True).exists():
            messages.error(request, 'Llena la cantidad autorizada de todas las líneas antes de aprobar.')
        else:
            proyeccion.estado = EstadoProyeccion.APROBADA
            proyeccion.aprobada_por = request.user  # queda registrado quién aprobó
            proyeccion.fecha_aprobacion = timezone.now()
            proyeccion.save(update_fields=['estado', 'aprobada_por', 'fecha_aprobacion'])
            registrar(request.user, AccionBitacora.APROBAR, proyeccion, 'estado', EstadoProyeccion.ENVIADA, 
                      EstadoProyeccion.APROBADA)     
            messages.success(request, 'Proyección aprobada.')
    return redirect('proyecciones:revisar', pk=proyeccion.pk)


@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)   
def abrir_periodo_vista(request):
    if request.method == 'POST':
        form = AbrirPeriodoForm(request.POST)
        if form.is_valid():
            periodo, creadas = abrir_periodo(
            form.cleaned_data['anio'],
            form.cleaned_data['fecha_limite'],
            request.user,)
            messages.success(
                request,
                f'Periodo {periodo.anio}: se crearon {creadas} proyecciones en borrador.',
            )
            return redirect('proyecciones:revision')
    else:
        form = AbrirPeriodoForm(initial={'anio': date.today().year + 1})
    return render(request, 'proyecciones/abrir_periodo.html', {'form': form})

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def corregir_linea(request, pk):
    """Los administradores cambian cualquier dato de una línea enviada o aprobada, con justificación."""
    linea = get_object_or_404(Linea, pk=pk)
    proyeccion = linea.proyeccion
    if proyeccion.estado == EstadoProyeccion.BORRADOR:
        messages.error(request, 'Esa proyección sigue en borrador: la edita el área.')
        return redirect('proyecciones:revision')
    antes = valores_linea(linea)  # la foto se toma ANTES de crear el formulario
    form = CorreccionLineaForm(request.POST or None, instance=linea)
    if request.method == 'POST' and form.is_valid():
        cambios = guardar_correccion(form.save(commit=False), antes, request.user, form.cleaned_data['motivo'])
        if cambios:
            messages.success(request, f'Se guardaron {cambios} cambios con su justificación.')
        else:
            messages.info(request, 'No cambiaste ningún dato.')
        return redirect('proyecciones:revisar', pk=proyeccion.pk)
    titulo = 'Ajustar línea' if proyeccion.estado == EstadoProyeccion.APROBADA else 'Corregir línea'
    return render(request, 'proyecciones/linea_form.html', {
        'form': form, 'proyeccion': proyeccion, 'titulo': titulo, 'sugeridos': _nombres_sugeridos(),
        'volver': reverse('proyecciones:revisar', args=[proyeccion.pk]),
    })
    
@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def alternar_periodo_vista(request, pk):
    periodo = get_object_or_404(Periodo, pk=pk)
    if request.method == 'POST':  # solo con el botón, nunca con solo abrir un enlace
        alternar_periodo(periodo, request.user)
        messages.success(request, f'Periodo {periodo.anio}: {periodo.get_estado_display().lower()}.')
    return redirect('proyecciones:revision')

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def bitacora(request):
    """Los últimos 200 movimientos, con nombres legibles."""
    filas = Bitacora.objects.select_related('usuario')[:200]
    for fila in filas:
        fila.objeto = nombre_registro(fila.tabla, fila.registro_id)
        fila.campo_legible = nombre_campo(fila.campo) if fila.campo else ''
    return render(request, 'proyecciones/bitacora.html', {'filas': filas})

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def consolidado_vista(request):
    """Consolidado de un año: cada área por separado y la suma por producto."""
    periodos = Periodo.objects.all()
    anio = request.GET.get('anio', '')
    periodo = get_object_or_404(Periodo, anio=anio) if anio.isdigit() else periodos.first()
    contexto = {'periodos': periodos, 'periodo': periodo, 'meses': MESES_CORTOS}
    if periodo:
        areas = consolidado_por_area(periodo)
        contexto.update({
            'areas': areas,
            'productos': consolidado_por_producto(periodo),
            'costo_general': sum(a['costo_total'] for a in areas),
            'pendientes': periodo.proyecciones.filter(estado=EstadoProyeccion.BORRADOR).select_related('area'),
        })
    return render(request, 'proyecciones/consolidado.html', contexto)

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def descargar_consolidado(request, anio):
    """Descarga el consolidado del año en Excel."""
    periodo = get_object_or_404(Periodo, anio=anio)
    respuesta = HttpResponse(
        construir_excel(periodo),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    respuesta['Content-Disposition'] = f'attachment; filename="Consolidado_proyeccion_{periodo.anio}.xlsx"'
    return respuesta

