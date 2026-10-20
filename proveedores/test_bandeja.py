import shutil
import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from cuentas.models import Rol, Usuario
from proveedores.models import Categoria, DocumentoProveedor, EnvioProveedor, Proveedor, TipoDocumento

# Los PDF de las pruebas van a una carpeta temporal, no a archivos_privados/.
CARPETA_PRUEBAS = tempfile.mkdtemp()
PDF = b"%PDF-1.4\n% documento inventado para pruebas\n"
CLAVE = "Suministros-Prueba-2026"


def pdf(nombre="RUT 2026.pdf"):
    return SimpleUploadedFile(nombre, PDF, content_type="application/pdf")


@override_settings(MEDIA_ROOT=CARPETA_PRUEBAS)
class BaseBandejaTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(CARPETA_PRUEBAS, ignore_errors=True)

    def setUp(self):
        categoria = Categoria.objects.get(nombre="Proveedores Generales")
        self.proveedor = Proveedor.objects.create(nit="900123456-7", razon_social="Proveedor Ficticio SAS", tipo_persona="juridica", categoria=categoria)
        # Tipos propios de estas pruebas, para no depender del catálogo cargado en la migración.
        self.rut = TipoDocumento.objects.create(nombre="Tipo de prueba que vence", vence=True)
        self.camara = TipoDocumento.objects.create(nombre="Tipo de prueba con vigencia", vence=True, vigencia_dias=30)
        self.admin = Usuario.objects.create_user("admin@ejemplo.com", "Admin", CLAVE, rol=Rol.ADMINISTRADOR)
        self.dev = Usuario.objects.create_user("dev@ejemplo.com", "Dev", CLAVE, rol=Rol.DESARROLLADOR)
        self.client.force_login(self.admin)

    def nuevo_envio(self, **datos):
        datos = {"origen": "portal", "proveedor": self.proveedor, "nit": "900123456-7", "razon_social": "Proveedor Ficticio SAS",
                 "tipo": self.rut, "archivo": pdf(), **datos}
        return EnvioProveedor.objects.create(**datos)

    def procesar(self, envio, **datos):
        datos = {"proveedor": self.proveedor.pk, "fecha_expedicion": "2026-10-01", "fecha_vencimiento": "2027-10-01", **datos}
        return self.client.post(reverse("proveedores:envio_procesar", args=[envio.pk]), datos)


class PermisosBandejaTest(BaseBandejaTest):
    def test_sin_sesion_pide_ingresar(self):
        envio = self.nuevo_envio()
        self.client.logout()
        for nombre, args in [("bandeja", []), ("bandeja_detalle", [envio.pk]), ("envio_archivo", [envio.pk])]:
            self.assertEqual(self.client.get(reverse(f"proveedores:{nombre}", args=args)).status_code, 302)

    def test_coordinador_de_area_y_proveedor_no_entran(self):
        envio = self.nuevo_envio()
        otros = [
            Usuario.objects.create_user("coord@ejemplo.com", "Coord", CLAVE, rol=Rol.COORDINADOR),
            Usuario.objects.create_user("prov@ejemplo.com", "Prov", CLAVE, rol=Rol.PROVEEDOR, proveedor=self.proveedor),
        ]
        for usuario in otros:
            self.client.force_login(usuario)
            for nombre, args in [("bandeja", []), ("bandeja_detalle", [envio.pk]), ("envio_archivo", [envio.pk])]:
                self.assertEqual(self.client.get(reverse(f"proveedores:{nombre}", args=args)).status_code, 403)
            self.assertEqual(self.procesar(envio).status_code, 403)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, "pendiente")

    def test_administrador_y_desarrollador_entran(self):
        for usuario in (self.admin, self.dev):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("proveedores:bandeja")).status_code, 200)


class ListaBandejaTest(BaseBandejaTest):
    def test_por_defecto_muestra_solo_pendientes(self):
        self.nuevo_envio(razon_social="Pendiente SAS")
        self.nuevo_envio(razon_social="Descartado SAS", estado="descartado", motivo_descarte="Ilegible")
        respuesta = self.client.get(reverse("proveedores:bandeja"))
        self.assertContains(respuesta, "Pendiente SAS")
        self.assertNotContains(respuesta, "Descartado SAS")
        respuesta = self.client.get(reverse("proveedores:bandeja"), {"estado": ""})
        self.assertContains(respuesta, "Descartado SAS")


class VerPdfTest(BaseBandejaTest):
    def test_entrega_el_pdf_con_permiso(self):
        envio = self.nuevo_envio()
        respuesta = self.client.get(reverse("proveedores:envio_archivo", args=[envio.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertEqual(b"".join(respuesta.streaming_content), PDF)

    def test_archivo_que_ya_no_esta_da_404(self):
        envio = self.nuevo_envio()
        envio.archivo.delete(save=False)
        self.assertEqual(self.client.get(reverse("proveedores:envio_archivo", args=[envio.pk])).status_code, 404)

    def test_la_ruta_de_archivos_no_esta_publicada(self):
        envio = self.nuevo_envio()
        self.assertEqual(self.client.get("/archivos/" + envio.archivo.name).status_code, 404)


class ProcesarEnvioTest(BaseBandejaTest):
    def test_crea_el_documento_con_copia_del_pdf_y_marca_procesado(self):
        envio = self.nuevo_envio()
        respuesta = self.procesar(envio, observaciones="Revisado")
        self.assertRedirects(respuesta, reverse("proveedores:bandeja"))
        envio.refresh_from_db()
        documento = envio.documento
        self.assertEqual(envio.estado, "procesado")
        self.assertEqual(envio.revisado_por, self.admin)
        self.assertIsNotNone(envio.fecha_revision)
        self.assertEqual(documento.proveedor, self.proveedor)
        self.assertEqual(documento.tipo, self.rut)
        self.assertEqual(documento.fecha_vencimiento, date(2027, 10, 1))
        self.assertEqual(documento.registrado_por, self.admin)
        self.assertTrue(documento.archivo.name.startswith("documentos/"))
        self.assertNotEqual(documento.archivo.name, envio.archivo.name)
        with documento.archivo.open("rb") as copia:
            self.assertEqual(copia.read(), PDF)

    def test_documento_que_vence_exige_fecha(self):
        envio = self.nuevo_envio()
        respuesta = self.procesar(envio, fecha_vencimiento="")
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(DocumentoProveedor.objects.exists())
        envio.refresh_from_db()
        self.assertEqual(envio.estado, "pendiente")

    def test_calcula_el_vencimiento_si_el_tipo_tiene_vigencia(self):
        envio = self.nuevo_envio(tipo=self.camara)
        self.procesar(envio, fecha_expedicion="2026-10-01", fecha_vencimiento="")
        self.assertEqual(DocumentoProveedor.objects.get().fecha_vencimiento, date(2026, 10, 1) + timedelta(days=30))

    def test_envio_manual_sin_proveedor_se_vincula_al_elegido(self):
        envio = self.nuevo_envio(origen="manual", proveedor=None)
        self.procesar(envio)
        envio.refresh_from_db()
        self.assertEqual(envio.proveedor, self.proveedor)

    def test_proveedor_sugerido_aparece_preseleccionado(self):
        envio = self.nuevo_envio(origen="manual", proveedor=None, nit="900123456")
        respuesta = self.client.get(reverse("proveedores:bandeja_detalle", args=[envio.pk]))
        self.assertContains(respuesta, f'<option value="{self.proveedor.pk}" selected>')

    def test_no_se_procesa_dos_veces(self):
        envio = self.nuevo_envio()
        self.procesar(envio)
        self.procesar(envio)
        self.assertEqual(DocumentoProveedor.objects.count(), 1)

    def test_el_proveedor_ve_el_resultado_en_su_portal(self):
        envio = self.nuevo_envio()
        self.procesar(envio)
        usuario = Usuario.objects.create_user("prov@ejemplo.com", "Prov", CLAVE, rol=Rol.PROVEEDOR, proveedor=self.proveedor)
        self.client.force_login(usuario)
        self.assertContains(self.client.get(reverse("portal:inicio")), "Aceptado")


class DescartarEnvioTest(BaseBandejaTest):
    def test_descarta_con_motivo(self):
        envio = self.nuevo_envio()
        respuesta = self.client.post(reverse("proveedores:envio_descartar", args=[envio.pk]), {"motivo": "El documento está ilegible"})
        self.assertRedirects(respuesta, reverse("proveedores:bandeja"))
        envio.refresh_from_db()
        self.assertEqual(envio.estado, "descartado")
        self.assertEqual(envio.motivo_descarte, "El documento está ilegible")
        self.assertEqual(envio.revisado_por, self.admin)
        self.assertFalse(DocumentoProveedor.objects.exists())

    def test_sin_motivo_no_descarta(self):
        envio = self.nuevo_envio()
        respuesta = self.client.post(reverse("proveedores:envio_descartar", args=[envio.pk]), {"motivo": "   "})
        self.assertEqual(respuesta.status_code, 200)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, "pendiente")

    def test_uno_ya_procesado_no_se_descarta(self):
        envio = self.nuevo_envio()
        self.procesar(envio)
        self.client.post(reverse("proveedores:envio_descartar", args=[envio.pk]), {"motivo": "Tarde"})
        envio.refresh_from_db()
        self.assertEqual(envio.estado, "procesado")

    def test_get_no_cambia_nada(self):
        envio = self.nuevo_envio()
        self.client.get(reverse("proveedores:envio_descartar", args=[envio.pk]))
        self.client.get(reverse("proveedores:envio_procesar", args=[envio.pk]))
        envio.refresh_from_db()
        self.assertEqual(envio.estado, "pendiente")


class VerDocumentoDeLaFichaTest(BaseBandejaTest):
    def test_la_ficha_ofrece_ver_el_pdf_y_se_abre(self):
        envio = self.nuevo_envio()
        self.procesar(envio)
        documento = DocumentoProveedor.objects.get()
        ficha = self.client.get(reverse("proveedores:detalle", args=[self.proveedor.pk]))
        self.assertContains(ficha, reverse("proveedores:documento_archivo", args=[documento.pk]))
        respuesta = self.client.get(reverse("proveedores:documento_archivo", args=[documento.pk]))
        self.assertEqual(b"".join(respuesta.streaming_content), PDF)
