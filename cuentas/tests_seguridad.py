from django.test import TestCase
from django.urls import reverse

from cuentas.models import Rol, Usuario

CLAVE = 'Clave-Segura-2027'
NUEVA = 'Otra-Clave-Segura-2028'


class CambioDeClaveObligatorioTest(TestCase):

    def setUp(self):
        self.normal = Usuario.objects.create_user(
            'normal@ejemplo.test', 'Normal', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.nuevo = Usuario.objects.create_user(
            'nuevo@ejemplo.test', 'Nuevo', password=CLAVE, rol=Rol.ADMINISTRADOR, debe_cambiar_clave=True)

    def test_sin_marca_navega_normal(self):
        self.client.force_login(self.normal)
        self.assertEqual(self.client.get(reverse('proyecciones:revision')).status_code, 200)

    def test_con_marca_lo_mandan_a_cambiar_la_clave(self):
        self.client.force_login(self.nuevo)
        respuesta = self.client.get(reverse('proyecciones:revision'))
        self.assertRedirects(respuesta, reverse('cambiar_clave'))

    def test_con_marca_puede_ver_el_cambio_de_clave_y_salir(self):
        self.client.force_login(self.nuevo)
        self.assertEqual(self.client.get(reverse('cambiar_clave')).status_code, 200)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 302)

    def test_cambiar_la_clave_quita_la_marca(self):
        self.client.force_login(self.nuevo)
        respuesta = self.client.post(reverse('cambiar_clave'), {
            'old_password': CLAVE, 'new_password1': NUEVA, 'new_password2': NUEVA})
        self.assertRedirects(respuesta, reverse('inicio'))
        self.nuevo.refresh_from_db()
        self.assertFalse(self.nuevo.debe_cambiar_clave)
        self.assertTrue(self.nuevo.check_password(NUEVA))
        self.assertEqual(self.client.get(reverse('proyecciones:revision')).status_code, 200)

    def test_no_deja_repetir_la_clave_temporal(self):
        self.client.force_login(self.nuevo)
        respuesta = self.client.post(reverse('cambiar_clave'), {
            'old_password': CLAVE, 'new_password1': CLAVE, 'new_password2': CLAVE})
        self.assertEqual(respuesta.status_code, 200)
        self.nuevo.refresh_from_db()
        self.assertTrue(self.nuevo.debe_cambiar_clave)


class MarcaDesdeUsuariosTest(TestCase):

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.otro = Usuario.objects.create_user(
            'otro@ejemplo.test', 'Otro', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.client.force_login(self.admin)

    def test_usuario_nuevo_debe_cambiar_la_clave(self):
        self.client.post(reverse('configuracion:usuario_nuevo'), {
            'correo': 'creado@ejemplo.test', 'nombre': 'Creado', 'rol': Rol.ADMINISTRADOR,
            'area': '', 'password1': CLAVE, 'password2': CLAVE})
        self.assertTrue(Usuario.objects.get(correo='creado@ejemplo.test').debe_cambiar_clave)

    def test_clave_puesta_por_un_admin_es_temporal(self):
        self.client.post(reverse('configuracion:usuario_clave', args=[self.otro.pk]), {
            'new_password1': NUEVA, 'new_password2': NUEVA})
        self.otro.refresh_from_db()
        self.assertTrue(self.otro.debe_cambiar_clave)

    def test_cambiarse_la_propia_clave_no_activa_la_marca(self):
        self.client.post(reverse('configuracion:usuario_clave', args=[self.admin.pk]), {
            'new_password1': NUEVA, 'new_password2': NUEVA})
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.debe_cambiar_clave)


class BloqueoPorIntentosTest(TestCase):

    def setUp(self):
        Usuario.objects.create_user('admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        Usuario.objects.create_user('otro@ejemplo.test', 'Otro', password=CLAVE, rol=Rol.ADMINISTRADOR)

    def _intentar(self, correo, clave):
        return self.client.post(reverse('login'), {'username': correo, 'password': clave})

    def test_cinco_fallos_bloquean_aunque_luego_la_clave_sea_correcta(self):
        for _ in range(5):
            self._intentar('admin@ejemplo.test', 'mala')
        respuesta = self._intentar('admin@ejemplo.test', CLAVE)
        self.assertContains(respuesta, 'Acceso bloqueado', status_code=429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cuatro_fallos_todavia_no_bloquean(self):
        for _ in range(4):
            self._intentar('admin@ejemplo.test', 'mala')
        self.assertEqual(self._intentar('admin@ejemplo.test', CLAVE).status_code, 302)

    def test_el_bloqueo_es_solo_de_ese_correo(self):
        for _ in range(5):
            self._intentar('admin@ejemplo.test', 'mala')
        self.assertEqual(self._intentar('otro@ejemplo.test', CLAVE).status_code, 302)

    def test_un_ingreso_correcto_reinicia_la_cuenta(self):
        for _ in range(4):
            self._intentar('admin@ejemplo.test', 'mala')
        self._intentar('admin@ejemplo.test', CLAVE)
        self.client.logout()
        for _ in range(4):
            self._intentar('admin@ejemplo.test', 'mala')
        self.assertEqual(self._intentar('admin@ejemplo.test', CLAVE).status_code, 302)