import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from cuentas.models import Rol, Usuario
from proveedores.models import Categoria, EnvioProveedor, Proveedor, TipoDocumento

from .tests_portal import CLAVE, BasePortalTest

# Las pruebas guardan los PDF en una carpeta temporal, no en archivos_privados/.
CARPETA_PRUEBAS = tempfile.mkdtemp()
PDF = b"%PDF-1.4\n% documento inventado para pruebas\n"


def pdf(nombre="RUT 2026.pdf", contenido=PDF):
    return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")


def nuevo_proveedor(nit, razon_social="Otra Empresa Ficticia SAS"):
    categoria = Categoria.objects.get(nombre="Proveedores Generales")
    return Proveedor.objects.create(nit=nit, razon_social=razon_social, tipo_persona="juridica", categoria=categoria)


@override_settings(MEDIA_ROOT=CARPETA_PRUEBAS)
class SubirDocumentoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(CARPETA_PRUEBAS, ignore_errors=True)

    def setUp(self):
        self.rut = TipoDocumento.objects.get(nombre="RUT")
        self.proveedor = nuevo_proveedor("900123456-7", "Proveedor Ficticio SAS")
        self.usuario = Usuario.objects.create_user(
            "ana@proveedor-ficticio.test", "Ana Ficticia", CLAVE, rol=Rol.PROVEEDOR, proveedor=self.proveedor,
        )
        self.client.force_login(self.usuario)

    def subir(self, **datos):
        datos = {"tipo": self.rut.pk, "archivo": pdf(), **datos}
        return self.client.post(reverse("portal:inicio"), datos)

    def test_el_pdf_llega_a_la_bandeja_ligado_a_su_ficha(self):
        respuesta = self.subir()
        self.assertRedirects(respuesta, reverse("portal:inicio"))
        envio = EnvioProveedor.objects.get()
        self.assertEqual(envio.origen, "portal")
        self.assertEqual(envio.estado, "pendiente")
        self.assertEqual(envio.proveedor, self.proveedor)
        self.assertEqual(envio.nit, "900123456-7")
        self.assertEqual(envio.razon_social, "Proveedor Ficticio SAS")
        self.assertEqual(envio.nombre_original, "RUT 2026.pdf")

    def test_no_puede_cambiar_el_proveedor_ni_el_nit(self):
        otro = nuevo_proveedor("800999888-1")
        self.subir(proveedor=otro.pk, nit="800999888-1", razon_social="Otra", estado="procesado")
        envio = EnvioProveedor.objects.get()
        self.assertEqual(envio.proveedor, self.proveedor)
        self.assertEqual(envio.nit, "900123456-7")
        self.assertEqual(envio.estado, "pendiente")

    def test_rechaza_lo_que_no_es_pdf(self):
        respuesta = self.subir(archivo=pdf("foto.jpg"))
        self.assertEqual(respuesta.status_code, 200)
        self.subir(archivo=pdf("factura.pdf", b"MZ esto no es un PDF"))
        self.assertFalse(EnvioProveedor.objects.exists())

    def test_exige_tipo_y_archivo(self):
        self.client.post(reverse("portal:inicio"), {"tipo": self.rut.pk})
        self.client.post(reverse("portal:inicio"), {"archivo": pdf()})
        self.assertFalse(EnvioProveedor.objects.exists())

    def test_no_ofrece_tipos_de_documento_inactivos(self):
        self.rut.activo = False
        self.rut.save()
        self.subir()
        self.assertFalse(EnvioProveedor.objects.exists())
        respuesta = self.client.get(reverse("portal:inicio"))
        self.assertNotContains(respuesta, f'<option value="{self.rut.pk}"')

    def test_ve_la_lista_de_sus_envios_con_su_estado(self):
        self.subir()
        EnvioProveedor.objects.update(estado="descartado", motivo_descarte="El documento está ilegible")
        respuesta = self.client.get(reverse("portal:inicio"))
        self.assertContains(respuesta, "RUT 2026.pdf")
        self.assertContains(respuesta, "Rechazado")
        self.assertContains(respuesta, "El documento está ilegible")

    def test_no_ve_los_envios_de_otro_proveedor(self):
        otro = nuevo_proveedor("800999888-1")
        EnvioProveedor.objects.create(
            origen="portal", proveedor=otro, nit=otro.nit, razon_social=otro.razon_social,
            tipo=self.rut, archivo=pdf("secreto de otro.pdf"),
        )
        respuesta = self.client.get(reverse("portal:inicio"))
        self.assertNotContains(respuesta, "secreto de otro.pdf")
        self.assertContains(respuesta, "Todavía no ha enviado documentos")


class NitRepetidoTest(BasePortalTest):
    def test_sin_digito_contra_con_digito(self):
        nuevo_proveedor("900123456-7")
        self.registrar(nit="900123456")
        self.assertEqual(Proveedor.objects.count(), 1)

    def test_con_digito_contra_sin_digito(self):
        nuevo_proveedor("900123456")
        self.registrar(nit="900123456-7")
        self.assertEqual(Proveedor.objects.count(), 1)

    def test_acepta_puntos_y_espacios_y_los_quita(self):
        self.registrar(nit=" 900.123.456-7 ")
        self.assertTrue(Proveedor.objects.filter(nit="900123456-7").exists())

    def test_nit_parecido_si_registra(self):
        # 9001234567 es otro NIT: no debe confundirse con 900123456-7.
        nuevo_proveedor("900123456-7")
        self.registrar(nit="9001234567")
        self.assertEqual(Proveedor.objects.count(), 2)

    def test_la_ficha_interna_tambien_lo_revisa(self):
        nuevo_proveedor("900123456-7")
        repetido = Proveedor(nit="900123456", razon_social="Copia SAS", tipo_persona="juridica", categoria=self.categoria)
        with self.assertRaises(ValidationError) as error:
            repetido.full_clean()
        self.assertIn("nit", error.exception.message_dict)


class RegistroCategoriasTest(BasePortalTest):
    def test_no_ofrece_categorias_inactivas(self):
        self.categoria.activa = False
        self.categoria.save()
        respuesta = self.client.get(reverse("portal:registro"))
        self.assertNotContains(respuesta, "Proveedores Generales")
        self.registrar()
        self.assertFalse(Proveedor.objects.exists())

    def test_textos_en_usted(self):
        respuesta = self.client.get(reverse("portal:registro"))
        self.assertContains(respuesta, "Repita la clave")
        self.assertNotContains(respuesta, "si quieres")
        self.assertNotContains(respuesta, "inicias sesión")
