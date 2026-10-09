from django.test import TestCase
from django.urls import reverse

from areas.models import Area
from cuentas.models import Rol, Usuario
from proyecciones.models import ProductoSugerido


class ConfiguracionTest(TestCase):
    def setUp(self):
        self.area = Area.objects.create(nombre='Urgencias', codigo_area='URG')
        self.coord = Usuario.objects.create_user(
            'coord@ejemplo.test', 'Coord', password='x', rol=Rol.COORDINADOR, area=self.area)
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password='x', rol=Rol.ADMINISTRADOR)

    def test_coordinador_no_entra(self):
        self.client.force_login(self.coord)
        for nombre in ['panel', 'areas', 'unidades', 'productos']:
            respuesta = self.client.get(reverse(f'configuracion:{nombre}'))
            self.assertEqual(respuesta.status_code, 403, nombre)

    def test_administrador_entra(self):
        self.client.force_login(self.admin)
        for nombre in ['panel', 'areas', 'unidades', 'productos']:
            respuesta = self.client.get(reverse(f'configuracion:{nombre}'))
            self.assertEqual(respuesta.status_code, 200, nombre)

    def test_crear_area(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('configuracion:area_nueva'),
                         {'nombre': 'Laboratorio', 'codigo_area': 'LAB', 'activa': 'on'})
        self.assertTrue(Area.objects.filter(codigo_area='LAB').exists())

    def test_codigo_de_area_repetido_no_se_guarda(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('configuracion:area_nueva'),
                                     {'nombre': 'Otra', 'codigo_area': 'URG', 'activa': 'on'})
        self.assertEqual(respuesta.status_code, 200)  # vuelve al formulario con el error
        self.assertEqual(Area.objects.filter(codigo_area='URG').count(), 1)

    def test_desactivar_area_solo_con_post(self):
        self.client.force_login(self.admin)
        url = reverse('configuracion:area_alternar', args=[self.area.pk])
        self.client.get(url)
        self.area.refresh_from_db()
        self.assertTrue(self.area.activa)
        self.client.post(url)
        self.area.refresh_from_db()
        self.assertFalse(self.area.activa)

    def test_desactivar_producto(self):
        self.client.force_login(self.admin)
        producto = ProductoSugerido.objects.create(nombre='Guantes')
        self.client.post(reverse('configuracion:producto_alternar', args=[producto.pk]))
        producto.refresh_from_db()
        self.assertFalse(producto.activo)
        
CLAVE = 'Clave-Segura-2027'


class UsuariosTest(TestCase):
    def setUp(self):
        self.area = Area.objects.create(nombre='Urgencias', codigo_area='URG')
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.coord = Usuario.objects.create_user(
            'coord@ejemplo.test', 'Coord', password=CLAVE, rol=Rol.COORDINADOR, area=self.area)

    def _datos_nuevo(self, **cambios):
        datos = {'correo': 'nuevo@ejemplo.test', 'nombre': 'Nuevo', 'rol': Rol.COORDINADOR,
                 'area': self.area.pk, 'password1': CLAVE, 'password2': CLAVE}
        datos.update(cambios)
        return datos

    def test_coordinador_no_entra_a_usuarios(self):
        self.client.force_login(self.coord)
        respuesta = self.client.get(reverse('configuracion:usuarios'))
        self.assertEqual(respuesta.status_code, 403)

    def test_crear_coordinador_sin_area_se_rechaza(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('configuracion:usuario_nuevo'), self._datos_nuevo(area=''))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(correo='nuevo@ejemplo.test').exists())

    def test_crear_usuario_y_que_pueda_entrar(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('configuracion:usuario_nuevo'), self._datos_nuevo())
        self.assertTrue(Usuario.objects.filter(correo='nuevo@ejemplo.test').exists())
        self.client.logout()
        self.assertTrue(self.client.login(correo='nuevo@ejemplo.test', password=CLAVE))

    def test_cambiar_clave(self):
        self.client.force_login(self.admin)
        nueva = 'Otra-Clave-2028'
        self.client.post(reverse('configuracion:usuario_clave', args=[self.coord.pk]),
                         {'new_password1': nueva, 'new_password2': nueva})
        self.client.logout()
        self.assertTrue(self.client.login(correo='coord@ejemplo.test', password=nueva))
        self.client.logout()
        self.assertFalse(self.client.login(correo='coord@ejemplo.test', password=CLAVE))

    def test_desactivar_usuario_le_quita_el_acceso(self):
        self.client.force_login(self.admin)
        # sin el campo "activo" en el envío, el formulario lo toma como desmarcado
        self.client.post(reverse('configuracion:usuario_editar', args=[self.coord.pk]), {
            'nombre': 'Coord', 'correo': 'coord@ejemplo.test', 'rol': Rol.COORDINADOR, 'area': self.area.pk})
        self.client.logout()
        self.assertFalse(self.client.login(correo='coord@ejemplo.test', password=CLAVE))

    def test_nadie_se_desactiva_a_si_mismo(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('configuracion:usuario_editar', args=[self.admin.pk]), {
            'nombre': 'Admin', 'correo': 'admin@ejemplo.test', 'rol': Rol.ADMINISTRADOR})
        self.assertEqual(respuesta.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.activo)

    def test_nadie_se_cambia_su_propio_rol(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('configuracion:usuario_editar', args=[self.admin.pk]), {
            'nombre': 'Admin', 'correo': 'admin@ejemplo.test', 'rol': Rol.DESARROLLADOR, 'activo': 'on'})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol, Rol.ADMINISTRADOR)