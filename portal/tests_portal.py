from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario
from proveedores.models import Categoria, Proveedor

CLAVE = "Suministros-Prueba-2026"


class BasePortalTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.get(nombre="Proveedores Generales")

    def datos(self, **cambios):
        datos = {
            "nit": "900123456-7", "razon_social": "Proveedor Ficticio SAS", "tipo_persona": "juridica",
            "categoria": self.categoria.pk, "contacto_nombre": "Ana Ficticia",
            "correo": "ana@proveedor-ficticio.test", "contacto_telefono": "3000000000",
            "clave1": CLAVE, "clave2": CLAVE,
        }
        datos.update(cambios)
        return datos

    def registrar(self, **cambios):
        return self.client.post(reverse("portal:registro"), self.datos(**cambios))


class RegistroTest(BasePortalTest):
    def test_crea_la_ficha_en_revision_y_el_usuario_ligado(self):
        respuesta = self.registrar()
        self.assertRedirects(respuesta, reverse("portal:inicio"))
        proveedor = Proveedor.objects.get(nit="900123456-7")
        self.assertEqual(proveedor.estado, "en_revision")
        self.assertEqual(proveedor.contacto_correo, "ana@proveedor-ficticio.test")
        usuario = Usuario.objects.get(correo="ana@proveedor-ficticio.test")
        self.assertEqual(usuario.rol, Rol.PROVEEDOR)
        self.assertEqual(usuario.proveedor, proveedor)
        self.assertTrue(usuario.check_password(CLAVE))
        self.assertFalse(usuario.is_staff)

    def test_queda_con_sesion_iniciada_y_ve_su_portal(self):
        self.registrar()
        respuesta = self.client.get(reverse("portal:inicio"))
        self.assertContains(respuesta, "Proveedor Ficticio SAS")
        self.assertContains(respuesta, "En revisión")

    def test_nit_repetido_no_registra(self):
        Proveedor.objects.create(nit="900123456-7", razon_social="Otro SAS", tipo_persona="juridica", categoria=self.categoria)
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(rol=Rol.PROVEEDOR).exists())

    def test_correo_repetido_no_registra(self):
        Usuario.objects.create_user("ana@proveedor-ficticio.test", "Ana", CLAVE, rol=Rol.ADMINISTRADOR)
        self.registrar()
        self.assertFalse(Proveedor.objects.exists())

    def test_claves_distintas_o_debiles_no_registran(self):
        self.registrar(clave2="Otra-Clave-2026")
        self.registrar(clave1="12345678", clave2="12345678")
        self.assertFalse(Proveedor.objects.exists())

    def test_nit_con_letras_no_registra(self):
        self.registrar(nit="ABC123")
        self.assertFalse(Proveedor.objects.exists())

    def test_con_sesion_iniciada_no_muestra_el_registro(self):
        self.registrar()
        respuesta = self.client.get(reverse("portal:registro"))
        self.assertEqual(respuesta.status_code, 302)


class PermisosPortalTest(BasePortalTest):
    def setUp(self):
        super().setUp()
        self.registrar()
        self.proveedor_usuario = Usuario.objects.get(rol=Rol.PROVEEDOR)
        self.admin = Usuario.objects.create_user("admin@ejemplo.com", "Admin", CLAVE, rol=Rol.ADMINISTRADOR)

    def test_inicio_lleva_al_proveedor_a_su_portal(self):
        self.client.force_login(self.proveedor_usuario)
        self.assertRedirects(self.client.get(reverse("inicio")), reverse("portal:inicio"))

    def test_proveedor_no_entra_a_lo_interno(self):
        self.client.force_login(self.proveedor_usuario)
        self.assertEqual(self.client.get(reverse("proveedores:lista")).status_code, 403)
        self.assertEqual(self.client.get(reverse("proyecciones:revision")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_administrador_no_entra_al_portal(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("portal:inicio")).status_code, 403)

    def test_sin_sesion_el_portal_pide_ingresar(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("portal:inicio")).status_code, 302)
        self.assertEqual(self.client.get(reverse("portal:registro")).status_code, 200)
