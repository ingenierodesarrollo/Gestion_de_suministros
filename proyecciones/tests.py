from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from areas.models import Area
from cuentas.models import Rol, Usuario

from .models import EstadoProyeccion, Linea, Periodo, ProyeccionArea, UnidadMedida


class BaseProyeccionTest(TestCase):
    """Datos inventados que usan todas las pruebas. Viven solo en la base de prueba."""

    @classmethod
    def setUpTestData(cls):
        cls.urgencias = Area.objects.create(nombre='Urgencias', codigo_area='URG')
        cls.laboratorio = Area.objects.create(nombre='Laboratorio', codigo_area='LAB')
        cls.coord_urg = Usuario.objects.create_user('coord.urg@ejemplo.test', 'Coord Urgencias', 'clave-prueba', rol=Rol.COORDINADOR, area=cls.urgencias)
        cls.coord_lab = Usuario.objects.create_user('coord.lab@ejemplo.test', 'Coord Laboratorio', 'clave-prueba', rol=Rol.COORDINADOR, area=cls.laboratorio)
        cls.admin = Usuario.objects.create_user('admin@ejemplo.test', 'Admin Prueba', 'clave-prueba', rol=Rol.ADMINISTRADOR)
        cls.periodo = Periodo.objects.create(anio=2027, fecha_apertura=date(2026, 10, 1), fecha_limite=date(2026, 11, 30), abierto_por=cls.admin)
        cls.unidad = UnidadMedida.objects.create(nombre='Unidad')
        cls.proy_urg = ProyeccionArea.objects.create(periodo=cls.periodo, area=cls.urgencias, responsable=cls.coord_urg)

    def crear_linea(self, proyeccion, **cambios):
        """Crea una línea de ejemplo. Con **cambios se puede ajustar cualquier campo."""
        datos = {'producto': 'Guantes', 'unidad': self.unidad, 'ene': 10, 'precio_unitario_est': Decimal('1500')}
        datos.update(cambios)
        return Linea.objects.create(proyeccion=proyeccion, **datos)
    
class SeguridadPorAreaTest(BaseProyeccionTest):

    def test_coordinador_ve_su_area(self):
        self.client.force_login(self.coord_urg)
        respuesta = self.client.get(reverse('proyecciones:detalle', args=[self.proy_urg.pk]))
        self.assertEqual(respuesta.status_code, 200)

    def test_coordinador_no_ve_otra_area(self):
        self.client.force_login(self.coord_lab)
        respuesta = self.client.get(reverse('proyecciones:detalle', args=[self.proy_urg.pk]))
        self.assertEqual(respuesta.status_code, 403)    
    
class EnviarTest(BaseProyeccionTest):

    def test_no_se_envia_sin_lineas(self):
        self.client.force_login(self.coord_urg)
        self.client.post(reverse('proyecciones:enviar', args=[self.proy_urg.pk]))
        self.proy_urg.refresh_from_db()
        self.assertEqual(self.proy_urg.estado, EstadoProyeccion.BORRADOR)

    def test_se_envia_con_lineas(self):
        self.crear_linea(self.proy_urg)
        self.client.force_login(self.coord_urg)
        self.client.post(reverse('proyecciones:enviar', args=[self.proy_urg.pk]))
        self.proy_urg.refresh_from_db()
        self.assertEqual(self.proy_urg.estado, EstadoProyeccion.ENVIADA)
        self.assertIsNotNone(self.proy_urg.fecha_envio)


class LoEnviadoNoSeTocaTest(BaseProyeccionTest):

    def setUp(self):
        self.linea = self.crear_linea(self.proy_urg)
        self.proy_urg.estado = EstadoProyeccion.ENVIADA
        self.proy_urg.save()
        self.client.force_login(self.coord_urg)

    def test_no_agrega_lineas(self):
        respuesta = self.client.get(reverse('proyecciones:agregar_linea', args=[self.proy_urg.pk]))
        self.assertEqual(respuesta.status_code, 403)

    def test_no_edita_lineas(self):
        respuesta = self.client.post(reverse('proyecciones:editar_linea', args=[self.linea.pk]), {'producto': 'Cambiado'})
        self.assertEqual(respuesta.status_code, 403)
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.producto, 'Guantes')

    def test_no_borra_lineas(self):
        respuesta = self.client.post(reverse('proyecciones:borrar_linea', args=[self.linea.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Linea.objects.filter(pk=self.linea.pk).exists())
    