from django.test import TestCase
from django.urls import reverse

from areas.models import Area
from cuentas.models import Rol, Usuario

CLAVE = 'Clave-Segura-2027'


class CuentasTest(TestCase):
    def setUp(self):
        area = Area.objects.create(nombre='Urgencias', codigo_area='URG')
        self.coord = Usuario.objects.create_user(
            'coord@ejemplo.test', 'Coord', password=CLAVE, rol=Rol.COORDINADOR, area=area)
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.dev = Usuario.objects.create_superuser('dev@ejemplo.test', 'Dev', password=CLAVE)

    def test_login_correcto_va_al_inicio(self):
        respuesta = self.client.post(reverse('login'), {'username': 'coord@ejemplo.test', 'password': CLAVE})
        self.assertRedirects(respuesta, reverse('inicio'))

    def test_clave_incorrecta_no_entra(self):
        respuesta = self.client.post(reverse('login'), {'username': 'coord@ejemplo.test', 'password': 'mala'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_usuario_desactivado_no_entra(self):
        self.coord.activo = False
        self.coord.save()
        respuesta = self.client.post(reverse('login'), {'username': 'coord@ejemplo.test', 'password': CLAVE})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_inicio_sin_sesion_manda_al_login(self):
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_coordinador_no_ve_administracion(self):
        self.client.force_login(self.coord)
        self.assertNotContains(self.client.get(reverse('inicio')), 'Bitácora')

    def test_administrador_y_desarrollador_ven_administracion(self):
        for usuario in (self.admin, self.dev):
            self.client.force_login(usuario)
            self.assertContains(self.client.get(reverse('inicio')), 'Bitácora')

    def test_coordinador_no_entra_a_revision(self):
        self.client.force_login(self.coord)
        self.assertEqual(self.client.get(reverse('proyecciones:revision')).status_code, 403)

    def test_administrador_y_desarrollador_entran_al_admin_de_django(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        self.client.force_login(self.dev)
        self.assertEqual(self.client.get('/admin/').status_code, 200)
