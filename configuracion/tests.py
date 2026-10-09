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