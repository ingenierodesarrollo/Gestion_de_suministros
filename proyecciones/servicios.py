from datetime import date
from django.db import transaction
from areas.models import Area
from .models import AccionBitacora, Ajuste, Bitacora, EstadoProyeccion, EstadoPeriodo, Linea, Periodo, ProyeccionArea
from cuentas.models import Rol, Usuario


@transaction.atomic
def abrir_periodo(anio, fecha_limite, usuario):
    """Crea el periodo (si no existe) y una proyección en borrador por cada área activa.
    Lo que ya existe no se toca. Devuelve (periodo, cantidad_creadas)."""
    periodo, periodo_nuevo = Periodo.objects.get_or_create(
        anio=anio,
        defaults={
            'fecha_apertura': date.today(),
            'fecha_limite': fecha_limite,
            'abierto_por': usuario,
        },
    )
    creadas = 0
    for area in Area.objects.filter(activa=True):
        coordinador = Usuario.objects.filter(area=area, rol=Rol.COORDINADOR, activo=True).first()
        _, nueva = ProyeccionArea.objects.get_or_create(
            periodo=periodo,
            area=area,
            defaults={'responsable': coordinador or usuario},
        )
        if nueva:
            creadas += 1
    if periodo_nuevo or creadas:
        registrar(usuario, AccionBitacora.ABRIR, periodo, 'proyecciones creadas', None, creadas)
    return periodo, creadas

CAMPOS_LINEA = ['producto', 'dependencia', 'serie', 'unidad', *Linea.MESES,
                'precio_unitario_est', 'cantidad_autorizada']


def _texto(valor):
    return '' if valor is None else str(valor)[:200]


def registrar(usuario, accion, objeto, campo='', antes=None, despues=None, motivo=''):
    """Agrega una fila a la bitácora. Nunca edita ni borra filas."""
    Bitacora.objects.create(
        usuario=usuario, accion=accion, tabla=objeto._meta.model_name, registro_id=objeto.pk,
        campo=campo, valor_anterior=_texto(antes), valor_nuevo=_texto(despues), motivo=motivo,
    )


def valores_linea(linea):
    """Foto de la línea antes de cambiarla, para comparar después."""
    return {campo: getattr(linea, campo) for campo in CAMPOS_LINEA}


@transaction.atomic
def guardar_correccion(linea, antes, usuario, motivo):
    """Guarda la línea ya cambiada y deja rastro de cada dato que cambió. Devuelve cuántos cambiaron."""
    linea.save()
    aprobada = linea.proyeccion.estado == EstadoProyeccion.APROBADA
    accion = AccionBitacora.AJUSTAR if aprobada else AccionBitacora.CORREGIR
    cambios = 0
    for campo, valor_antes in antes.items():
        valor_ahora = getattr(linea, campo)
        if valor_ahora == valor_antes:
            continue
        cambios += 1
        if aprobada:
            Ajuste.objects.create(
                linea=linea, campo=campo, valor_aprobado=_texto(valor_antes),
                valor_nuevo=_texto(valor_ahora), justificacion=motivo, hecho_por=usuario,
            )
        registrar(usuario, accion, linea, campo, valor_antes, valor_ahora, motivo)
    return cambios

@transaction.atomic
def alternar_periodo(periodo, usuario):
    """Cierra el periodo si está abierto, o lo reabre si está cerrado. Deja rastro en la bitácora."""
    antes = periodo.estado
    if antes == EstadoPeriodo.ABIERTO:
        periodo.estado = EstadoPeriodo.CERRADO
        accion = AccionBitacora.CERRAR
    else:
        periodo.estado = EstadoPeriodo.ABIERTO
        accion = AccionBitacora.ABRIR
    periodo.save(update_fields=['estado'])
    registrar(usuario, accion, periodo, 'estado', antes, periodo.estado)
    return periodo

def registrar_cambios(usuario, accion, linea, antes):
    """Anota en la bitácora cada dato de la línea que cambió respecto a la foto 'antes'."""
    for campo, valor_antes in antes.items():
        valor_ahora = getattr(linea, campo)
        if valor_ahora != valor_antes:
            registrar(usuario, accion, linea, campo, valor_antes, valor_ahora)
            
def nombre_registro(tabla, registro_id):
    """Convierte tabla + número en un texto legible."""
    if tabla == 'periodo':
        periodo = Periodo.objects.filter(pk=registro_id).first()
        return f'Periodo {periodo.anio}' if periodo else f'Periodo n.º {registro_id}'
    if tabla == 'proyeccionarea':
        proy = ProyeccionArea.objects.select_related('area', 'periodo').filter(pk=registro_id).first()
        return f'Proyección {proy.area.nombre} {proy.periodo.anio}' if proy else f'Proyección n.º {registro_id}'
    if tabla == 'linea':
        linea = Linea.objects.select_related('proyeccion__area', 'proyeccion__periodo').filter(pk=registro_id).first()
        if linea:
            return f'{linea.producto} ({linea.proyeccion.area.nombre} {linea.proyeccion.periodo.anio})'
        return f'Línea n.º {registro_id} (ya borrada)'
    return f'{tabla} n.º {registro_id}'


def nombre_campo(campo):
    """Nombre del campo como lo ve el usuario (ej. 'ene' -> 'enero')."""
    for modelo in (Linea, ProyeccionArea):
        try:
            return str(modelo._meta.get_field(campo).verbose_name).capitalize()
        except Exception:
            continue
    return campo
    