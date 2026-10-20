from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from proveedores.models import Categoria, DocumentoProveedor, Proveedor, TipoDocumento


def crear_proveedor(nit="900111222-3"):
    categoria = Categoria.objects.get(nombre="Proveedores Generales")
    return Proveedor.objects.create(
        nit=nit, razon_social="Proveedor de Prueba SAS", tipo_persona="juridica", categoria=categoria,
    )


class ProveedorTests(TestCase):
    def test_nit_no_se_repite(self):
        crear_proveedor()
        with self.assertRaises(IntegrityError), transaction.atomic():
            crear_proveedor()

    def test_nit_valido_con_y_sin_digito_de_verificacion(self):
        for nit in ["900111222", "900111222-3"]:
            with self.subTest(nit=nit):
                proveedor = crear_proveedor(nit=nit)
                proveedor.full_clean()
                proveedor.delete()

    def test_nit_invalido(self):
        for nit in ["ABC123", "9001-11222", "900 111 222", "123", "900111222-33"]:
            with self.subTest(nit=nit):
                proveedor = crear_proveedor(nit="900111222")
                proveedor.nit = nit
                with self.assertRaises(ValidationError):
                    proveedor.full_clean()
                proveedor.delete()

    def test_estado_inicial_en_revision(self):
        self.assertEqual(crear_proveedor().estado, "en_revision")

    def test_texto_del_proveedor(self):
        self.assertEqual(str(crear_proveedor()), "Proveedor de Prueba SAS (900111222-3)")

    def test_no_se_borra_una_categoria_en_uso(self):
        proveedor = crear_proveedor()
        with self.assertRaises(ProtectedError):
            proveedor.categoria.delete()


class TipoDocumentoTests(TestCase):
    def test_valores_por_defecto(self):
        tipo = TipoDocumento.objects.create(nombre="Documento nuevo de prueba")
        self.assertTrue(tipo.vence)
        self.assertTrue(tipo.activo)
        self.assertIsNone(tipo.vigencia_dias)
        self.assertIsNone(tipo.requisito)

    def test_nombre_unico(self):
        # "RUT" ya existe por la migración 0004: no se puede crear otro igual.
        with self.assertRaises(IntegrityError), transaction.atomic():
            TipoDocumento.objects.create(nombre="RUT")


class DocumentoProveedorTests(TestCase):
    def setUp(self):
        self.proveedor = crear_proveedor()
        # Los tipos de documento ya existen: los cargó la migración 0004.
        self.rut = TipoDocumento.objects.create(nombre="Documento de prueba que vence", vence=True)
        self.portafolio = TipoDocumento.objects.create(nombre="Documento de prueba que no vence", vence=False)
        self.hoy = date(2026, 10, 19)

    def documento(self, tipo, vencimiento=None, expedicion=None):
        return DocumentoProveedor(
            proveedor=self.proveedor, tipo=tipo, fecha_vencimiento=vencimiento,
            fecha_expedicion=expedicion, enlace_drive="https://drive.google.com/prueba",
        )

    def test_tipo_que_vence_exige_fecha(self):
        with self.assertRaises(ValidationError) as error:
            self.documento(self.rut).full_clean()
        self.assertIn("fecha_vencimiento", error.exception.message_dict)

    def test_tipo_que_vence_con_fecha_es_valido(self):
        self.documento(self.rut, vencimiento=self.hoy + timedelta(days=100)).full_clean()

    def test_tipo_que_no_vence_acepta_sin_fecha(self):
        self.documento(self.portafolio).full_clean()

    def test_vencimiento_no_antes_de_expedicion(self):
        doc = self.documento(self.rut, vencimiento=date(2026, 1, 1), expedicion=date(2026, 2, 1))
        with self.assertRaises(ValidationError):
            doc.full_clean()

    def test_enlace_debe_ser_una_url(self):
        doc = self.documento(self.portafolio)
        doc.enlace_drive = "no es un enlace"
        with self.assertRaises(ValidationError):
            doc.full_clean()

    def test_estado_vigencia(self):
        casos = [
            (None, "sin_vencimiento"),
            (self.hoy - timedelta(days=1), "vencido"),
            (self.hoy, "por_vencer"),
            (self.hoy + timedelta(days=30), "por_vencer"),
            (self.hoy + timedelta(days=31), "vigente"),
        ]
        for vencimiento, esperado in casos:
            with self.subTest(vencimiento=vencimiento):
                self.assertEqual(self.documento(self.rut, vencimiento).estado_vigencia(self.hoy), esperado)

    def test_no_se_borra_un_tipo_en_uso(self):
        self.documento(self.rut, self.hoy + timedelta(days=100)).save()
        with self.assertRaises(ProtectedError):
            self.rut.delete()

    def test_al_borrar_el_proveedor_se_borran_sus_documentos(self):
        self.documento(self.rut, self.hoy + timedelta(days=100)).save()
        self.proveedor.delete()
        self.assertEqual(DocumentoProveedor.objects.count(), 0)
