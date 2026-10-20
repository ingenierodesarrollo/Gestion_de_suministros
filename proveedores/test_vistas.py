from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from areas.models import Area
from cuentas.models import Rol, Usuario
from proveedores.models import Categoria, DocumentoProveedor, Proveedor, TipoDocumento
from proveedores.servicios import documentos_actuales, resumen_vigencia


def nuevo_proveedor(nit="900111222-3", nombre="Proveedor de Prueba SAS"):
    categoria = Categoria.objects.get(nombre="Proveedores Generales")
    return Proveedor.objects.create(nit=nit, razon_social=nombre, tipo_persona="juridica", categoria=categoria)


def nuevo_documento(proveedor, tipo, dias, enlace="https://drive.google.com/prueba"):
    """Crea un documento que vence dentro de `dias` días (negativo = ya venció)."""
    vencimiento = timezone.localdate() + timedelta(days=dias)
    return DocumentoProveedor.objects.create(
        proveedor=proveedor, tipo=tipo, fecha_vencimiento=vencimiento, enlace_drive=enlace,
    )


class BaseVistasTest(TestCase):
    def setUp(self):
        area = Area.objects.create(nombre="Urgencias", codigo_area="URG")
        self.admin = Usuario.objects.create_user("admin@ejemplo.com", "Admin", "clave-segura-1", rol=Rol.ADMINISTRADOR)
        self.dev = Usuario.objects.create_user("dev@ejemplo.com", "Dev", "clave-segura-1", rol=Rol.DESARROLLADOR)
        self.coord = Usuario.objects.create_user("coord@ejemplo.com", "Coord", "clave-segura-1", rol=Rol.COORDINADOR, area=area)
        self.rut = TipoDocumento.objects.get(nombre="RUT")
        self.camara = TipoDocumento.objects.get(nombre="Certificado de Cámara de Comercio")


class PermisosTest(BaseVistasTest):
    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("proveedores:lista"))
        self.assertEqual(respuesta.status_code, 302)

    def test_coordinador_de_area_no_entra(self):
        proveedor = nuevo_proveedor()
        self.client.force_login(self.coord)
        for nombre, args in [("lista", []), ("nuevo", []), ("detalle", [proveedor.pk]), ("editar", [proveedor.pk])]:
            with self.subTest(vista=nombre):
                self.assertEqual(self.client.get(reverse(f"proveedores:{nombre}", args=args)).status_code, 403)

    def test_administrador_y_desarrollador_entran(self):
        for usuario in (self.admin, self.dev):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("proveedores:lista")).status_code, 200)


class ListaTest(BaseVistasTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.uno = nuevo_proveedor("900111222-3", "Lavandería Uno SAS")
        self.dos = nuevo_proveedor("800555666-1", "Aseo Dos SAS")

    def test_muestra_todos(self):
        respuesta = self.client.get(reverse("proveedores:lista"))
        self.assertContains(respuesta, "Lavandería Uno SAS")
        self.assertContains(respuesta, "Aseo Dos SAS")

    def test_busca_por_nombre_y_por_nit(self):
        respuesta = self.client.get(reverse("proveedores:lista"), {"q": "lavander"})
        self.assertContains(respuesta, "Lavandería Uno SAS")
        self.assertNotContains(respuesta, "Aseo Dos SAS")
        respuesta = self.client.get(reverse("proveedores:lista"), {"q": "800555"})
        self.assertContains(respuesta, "Aseo Dos SAS")
        self.assertNotContains(respuesta, "Lavandería Uno SAS")

    def test_filtra_por_estado(self):
        self.dos.estado = "aprobado"
        self.dos.save()
        respuesta = self.client.get(reverse("proveedores:lista"), {"estado": "aprobado"})
        self.assertContains(respuesta, "Aseo Dos SAS")
        self.assertNotContains(respuesta, "Lavandería Uno SAS")

    def test_avisa_de_documentos_vencidos(self):
        nuevo_documento(self.uno, self.rut, -5)
        respuesta = self.client.get(reverse("proveedores:lista"))
        self.assertContains(respuesta, "1 vencido")


class GuardarTest(BaseVistasTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.categoria = Categoria.objects.get(nombre="Proveedores Generales")

    def datos(self, **cambios):
        datos = {
            "nit": "900111222-3", "razon_social": "Proveedor Nuevo SAS", "tipo_persona": "juridica",
            "categoria": self.categoria.pk, "contacto_nombre": "", "contacto_correo": "",
            "contacto_telefono": "", "estado": "en_revision",
        }
        datos.update(cambios)
        return datos

    def test_crear(self):
        respuesta = self.client.post(reverse("proveedores:nuevo"), self.datos())
        proveedor = Proveedor.objects.get()
        self.assertRedirects(respuesta, reverse("proveedores:detalle", args=[proveedor.pk]))

    def test_nit_repetido_no_se_guarda(self):
        nuevo_proveedor()
        respuesta = self.client.post(reverse("proveedores:nuevo"), self.datos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Proveedor.objects.count(), 1)

    def test_nit_invalido_no_se_guarda(self):
        self.client.post(reverse("proveedores:nuevo"), self.datos(nit="ABC"))
        self.assertEqual(Proveedor.objects.count(), 0)

    def test_editar(self):
        proveedor = nuevo_proveedor()
        self.client.post(reverse("proveedores:editar", args=[proveedor.pk]), self.datos(estado="aprobado"))
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.estado, "aprobado")


class DetalleTest(BaseVistasTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.proveedor = nuevo_proveedor()

    def test_muestra_documento_con_su_estado_y_enlace(self):
        nuevo_documento(self.proveedor, self.rut, 100, enlace="https://drive.google.com/ejemplo-rut")
        respuesta = self.client.get(reverse("proveedores:detalle", args=[self.proveedor.pk]))
        self.assertContains(respuesta, "RUT")
        self.assertContains(respuesta, "Vigente")
        self.assertContains(respuesta, "https://drive.google.com/ejemplo-rut")

    def test_sin_documentos(self):
        respuesta = self.client.get(reverse("proveedores:detalle", args=[self.proveedor.pk]))
        self.assertContains(respuesta, "aún no tiene documentos")

    def test_proveedor_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse("proveedores:detalle", args=[9999])).status_code, 404)


class ServiciosTest(BaseVistasTest):
    def test_solo_cuenta_el_documento_mas_reciente_de_cada_tipo(self):
        proveedor = nuevo_proveedor()
        viejo = nuevo_documento(proveedor, self.rut, -200)
        nuevo = nuevo_documento(proveedor, self.rut, 300)
        actuales = documentos_actuales(proveedor)
        self.assertEqual(actuales, [nuevo])
        self.assertNotIn(viejo, actuales)
        self.assertEqual(resumen_vigencia(actuales)["vencido"], 0)

    def test_resumen_cuenta_cada_estado(self):
        proveedor = nuevo_proveedor()
        nuevo_documento(proveedor, self.rut, -1)
        nuevo_documento(proveedor, self.camara, 10)
        sin_vencer = TipoDocumento.objects.get(nombre="Portafolio de servicios")
        DocumentoProveedor.objects.create(proveedor=proveedor, tipo=sin_vencer, enlace_drive="https://drive.google.com/x")
        resumen = resumen_vigencia(documentos_actuales(proveedor))
        self.assertEqual(resumen, {"vigente": 0, "por_vencer": 1, "vencido": 1, "sin_vencimiento": 1})
