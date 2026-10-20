from datetime import date


def _orden(doc):
    """Qué tan reciente es un documento: primero por vencimiento (sin fecha = el más nuevo), luego por registro."""
    return (doc.fecha_vencimiento or date.max, doc.creado)


def documentos_actuales(proveedor):
    """El documento más reciente de cada tipo. Los anteriores (ya reemplazados) no cuentan para las alertas."""
    por_tipo = {}
    for doc in proveedor.documentos.all():
        actual = por_tipo.get(doc.tipo_id)
        if actual is None or _orden(doc) > _orden(actual):
            por_tipo[doc.tipo_id] = doc
    return sorted(por_tipo.values(), key=lambda doc: doc.tipo.nombre)


def resumen_vigencia(documentos, hoy=None):
    """Cuenta cuántos documentos hay en cada estado de vigencia."""
    resumen = {"vigente": 0, "por_vencer": 0, "vencido": 0, "sin_vencimiento": 0}
    for doc in documentos:
        resumen[doc.estado_vigencia(hoy)] += 1
    return resumen
