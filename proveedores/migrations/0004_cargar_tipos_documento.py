"""Carga la lista inicial de tipos de documento que se le piden a un proveedor.

Sale de los requisitos del FR-GDS-14 que son documentos, más SICOF, contrato y póliza (FR-GDS-28).
La vigencia es una SUPOSICIÓN inicial: la coordinadora debe confirmarla y se corrige desde el admin.
"""
from django.db import migrations

# (nombre, vence, vigencia_dias, número de requisito del FR-GDS-14 o None)
TIPOS = [
    ("Portafolio de servicios", False, None, 1),
    ("Certificado de Cámara de Comercio", True, 90, 2),
    ("RUT", False, None, 3),
    ("Certificación de sistema de gestión de calidad", True, None, 4),
    ("Cédula del representante legal", False, None, 5),
    ("Certificación bancaria", True, 90, 6),
    ("Referencias comerciales", True, 365, 7),
    ("Certificado de Buenas Prácticas de Manufactura", True, None, 8),
    ("Certificado de Buenas Prácticas de Elaboración", True, None, 9),
    ("Registro sanitario INVIMA", True, None, 10),
    ("Resolución del Fondo Rotatorio de Estupefacientes", True, None, 11),
    ("Fichas técnicas", False, None, 12),
    ("Certificado de habilitación", True, None, 13),
    ("Certificado de acreditación", True, None, 14),
    ("Políticas de devolución", False, None, 15),
    ("SARLAFT diligenciado", True, 365, 17),
    ("Última acta de visita del ente de control", True, 365, 18),
    ("Permisos ambientales", True, None, 19),
    ("Certificación ambiental (ISO 14001 u otra)", True, None, 20),
    ("Certificado de ciclo de vida", True, None, 21),
    ("Planilla de seguridad social", True, 30, 22),
    ("Certificado SG-SST de la ARL", True, 365, 23),
    ("Documentos de prevención de accidentes y plan de emergencia", True, 365, 24),
    ("Certificado de red contra incendios (Bomberos)", True, 365, 25),
    ("Certificados de competencias para trabajo de alto riesgo", True, None, 26),
    # Sin requisito en el FR-GDS-14: salen de la ficha de cotización FR-GDS-28.
    ("SICOF", True, 365, None),
    ("Contrato", True, None, None),
    ("Póliza", True, None, None),
]


def cargar(apps, schema_editor):
    Requisito = apps.get_model("proveedores", "Requisito")
    TipoDocumento = apps.get_model("proveedores", "TipoDocumento")
    for nombre, vence, vigencia_dias, numero in TIPOS:
        requisito = Requisito.objects.get(numero=numero) if numero else None
        TipoDocumento.objects.get_or_create(
            nombre=nombre,
            defaults={"vence": vence, "vigencia_dias": vigencia_dias, "requisito": requisito},
        )


class Migration(migrations.Migration):
    dependencies = [("proveedores", "0003_proveedor_tipodocumento_documentoproveedor")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
