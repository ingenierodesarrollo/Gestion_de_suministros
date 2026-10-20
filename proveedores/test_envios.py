import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from proveedores.models import Categoria, DocumentoProveedor, EnvioProveedor, Proveedor, TipoDocumento

# Las pruebas guardan los archivos en una carpeta temporal, no en archivos_privados/.
CARPETA_PRUEBAS = tempfile.mkdtemp()
PDF = b"%PDF-1.4\n% documento inventado para pruebas\n"


def archivo(nombre="RUT de prueba.pdf", contenido=PDF):
    return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")


def nuevo_proveedor(nit="900123456-7"):
    categoria = Categoria.objects.get(nombre="Proveedores Generales")
    return Proveedor.objects.create(nit=nit, razon_social="Proveedor Ficticio SAS", tipo_persona="juridica", categoria=categoria)


@override_settings(MEDIA_ROOT=CARPETA_PRUEBAS)
class BaseArchivosTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(CARPETA_PRUEBAS, ignore_errors=True)

    def setUp(self):
        self.rut = TipoDocumento.objects.get(nombre="RUT")


class EnvioProveedorTest(BaseArchivosTest):
    def nuevo_envio(self, **datos):
        datos = {"nit": "900123456-7", "razon_social": "Proveedor Ficticio SAS", "tipo": self.rut, "archivo": archivo(), **datos}
        return EnvioProveedor(**datos)

    def test_envio_valido_queda_pendiente_con_nombre_al_azar(self):
        envio = self.nuevo_envio()
        envio.full_clean()
        envio.save()
        self.assertEqual(envio.estado, "pendiente")
        self.assertEqual(envio.nombre_original, "RUT de prueba.pdf")
        self.assertTrue(envio.archivo.name.startswith("envios/"))
        self.assertNotIn("RUT", envio.archivo.name)
        with envio.archivo.open("rb") as guardado:
            self.assertEqual(guardado.read(), PDF)

    def test_rechaza_archivo_que_no_termina_en_pdf(self):
        envio = self.nuevo_envio(archivo=archivo("foto.jpg"))
        with self.assertRaises(ValidationError) as error:
            envio.full_clean()
        self.assertIn("archivo", error.exception.message_dict)

    def test_rechaza_archivo_disfrazado_de_pdf(self):
        envio = self.nuevo_envio(archivo=archivo("factura.pdf", b"MZ esto no es un PDF"))
        with self.assertRaises(ValidationError) as error:
            envio.full_clean()
        self.assertIn("archivo", error.exception.message_dict)

    def test_rechaza_archivo_de_mas_de_10_mb(self):
        grande = PDF + b"0" * (10 * 1024 * 1024)
        envio = self.nuevo_envio(archivo=archivo("grande.pdf", grande))
        with self.assertRaises(ValidationError) as error:
            envio.full_clean()
        self.assertIn("archivo", error.exception.message_dict)

    def test_descartar_exige_motivo(self):
        envio = self.nuevo_envio(estado="descartado")
        with self.assertRaises(ValidationError) as error:
            envio.full_clean()
        self.assertIn("motivo_descarte", error.exception.message_dict)
        envio.motivo_descarte = "Documento ilegible"
        envio.full_clean()

    def test_el_mismo_envio_del_portal_no_se_guarda_dos_veces(self):
        self.nuevo_envio(origen="portal", id_externo="P-1").save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.nuevo_envio(origen="portal", id_externo="P-1").save()

    def test_varios_envios_manuales_sin_id_externo(self):
        self.nuevo_envio().save()
        self.nuevo_envio().save()
        self.assertEqual(EnvioProveedor.objects.count(), 2)

    def test_sugiere_el_proveedor_con_el_mismo_nit(self):
        envio = self.nuevo_envio(nit=" 900123456-7 ")
        self.assertIsNone(envio.proveedor_sugerido())
        proveedor = nuevo_proveedor("900123456-7")
        self.assertEqual(envio.proveedor_sugerido(), proveedor)


class DocumentoConArchivoTest(BaseArchivosTest):
    def test_exige_archivo_o_enlace(self):
        documento = DocumentoProveedor(proveedor=nuevo_proveedor(), tipo=self.rut)
        with self.assertRaises(ValidationError):
            documento.full_clean()

    def test_basta_con_el_archivo(self):
        documento = DocumentoProveedor(proveedor=nuevo_proveedor(), tipo=self.rut, archivo=archivo())
        documento.full_clean()
        documento.save()
        self.assertTrue(documento.archivo.name.startswith("documentos/"))
