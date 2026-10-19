"""Carga el catálogo del FR-GDS-14: 11 categorías, 26 requisitos y la matriz de pesos.

Datos copiados de las hojas Evaluacion y M_pesos del Excel (con los errores de ortografía corregidos).
"""
from django.db import migrations

CATEGORIAS = [
    "Servicio de Lavanderia y Aseo",
    "Servicios de SG-SST",
    "Servicio de Seguridad y vigilancia",
    "Bancos de sangre",
    "Mantenimiento e infraestructura",
    "Servicio de Calibraciones",
    "Interdependencias / Laboratorios",
    "Servicio de Alimentacion Hospitalaria",
    "Proveedor de Servicio Farmaceutico y/ central de mezclas",
    "Servicio de Oxigenos y Aire Medicinal",
    "Proveedores Generales",
]

# (número, bloque, texto, pesos en el mismo orden que CATEGORIAS)
REQUISITOS = [
    (1, "calidad", "Portafolio de servicios",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (2, "calidad", "Certificado de Cámara de Comercio de existencia y representación legal",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (3, "calidad", "RUT",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (4, "calidad", "Certificacion en sistema de gestion de calidad",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (5, "calidad", "Fotocopia cedula del representante legal",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (6, "calidad", "Referencia o Certificacion Bancaria",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (7, "calidad", "Referencias comerciales",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (8, "calidad", "Certificado de Buenas Prácticas de Manufactura",
     [1, 1, 1, 2, 1, 1, 1, 1, 2, 2, 1]),
    (9, "calidad", "Certificación de Buenas Practicas de Elaboracion de medicamentos",
     [1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1]),
    (10, "calidad", "Registro sanitario vigente o en trámite de renovación de cada producto, expedido por el INVIMA ( Verificado en la página WEB INVIMA al momento de la recepción tecnica)",
     [1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1]),
    (11, "calidad", "Resolución de autorización del fondo Rotatorio de estupefacientes o quien haga sus veces para la fabricación y/o comercialización de Medicamentos de Control",
     [1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1]),
    (12, "calidad", "Fichas técnicas de equipos y productos",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2]),
    (13, "calidad", "Certificado de habilitacion",
     [1, 1, 1, 2, 1, 2, 2, 2, 2, 2, 1]),
    (14, "calidad", "Certificado de acreditacion",
     [1, 1, 1, 2, 1, 2, 1, 1, 1, 2, 1]),
    (15, "calidad", "Políticas de devolución",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (16, "calidad", "Ficha de cotizacion",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (17, "calidad", "Diligenciamiento de Sarlaft link",
     [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    (18, "calidad", "Ultima acta de visita por el ente de control",
     [2, 2, 1, 2, 1, 2, 2, 2, 2, 2, 2]),
    (19, "ambiental", "Permisos ambientales",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (20, "ambiental", "La empresa cuenta con certificado ISO 14001, sello verde u ecológico, certificación energética, carbono neutro u otras de tipo ambiental que den valor agregado o cuentan con un proceso de gestión ambiental.",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (21, "ambiental", "Certificado de Implementacion de ciclo de vida",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (22, "sgsst", "Planilla de pago de seguridad social",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (23, "sgsst", "Certificado de implementacion de nivel de cumplimiento del SGSST expedido por la ARL",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (24, "sgsst", "Listado de documentos para prevenir y atender incidentes, accidentes de trabajo, enfermedades laborales y plan de emergencia",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (25, "sgsst", "Certificado vigente de Red Contra incendios otorgada por Bomberos.",
     [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]),
    (26, "sgsst", "Certificados de competencias del personal que desarrollara trabajos de alto riesgo (espacios confinados, trabajo en caliente, electricidad) (si aplica)",
     [1, 2, 2, 1, 2, 1, 1, 1, 1, 1, 2]),
]


def cargar(apps, schema_editor):
    Categoria = apps.get_model("proveedores", "Categoria")
    Requisito = apps.get_model("proveedores", "Requisito")
    Peso = apps.get_model("proveedores", "Peso")
    categorias = [Categoria.objects.get_or_create(nombre=nombre)[0] for nombre in CATEGORIAS]
    for numero, bloque, texto, pesos in REQUISITOS:
        requisito, _ = Requisito.objects.get_or_create(
            numero=numero, defaults={"bloque": bloque, "texto": texto},
        )
        for categoria, valor in zip(categorias, pesos):
            Peso.objects.get_or_create(
                requisito=requisito, categoria=categoria, defaults={"valor": valor},
            )


class Migration(migrations.Migration):
    dependencies = [("proveedores", "0001_initial")]
    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
