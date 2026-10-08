from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from areas.models import Area
from cuentas.models import Rol, Usuario

from .models import EstadoProyeccion, Linea, Periodo, ProductoSugerido, ProyeccionArea, UnidadMedida


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
        
class RevisionTest(BaseProyeccionTest):

    def setUp(self):
        self.linea = self.crear_linea(self.proy_urg)
        self.proy_urg.estado = EstadoProyeccion.ENVIADA
        self.proy_urg.save()

    def test_coordinador_no_entra_a_revision(self):
        self.client.force_login(self.coord_urg)
        self.assertEqual(self.client.get(reverse('proyecciones:revision')).status_code, 403)
        self.assertEqual(self.client.get(reverse('proyecciones:revisar', args=[self.proy_urg.pk])).status_code, 403)

    def test_administrador_entra_a_revision(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('proyecciones:revision')).status_code, 200)

    def test_cero_es_un_autorizado_valido(self):
        self.client.force_login(self.admin)
        datos = {
            'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '0', 'form-MAX_NUM_FORMS': '1000',
            'form-0-id': self.linea.pk, 'form-0-cantidad_autorizada': '0',
        }
        self.client.post(reverse('proyecciones:revisar', args=[self.proy_urg.pk]), datos)
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.cantidad_autorizada, 0)


class AprobarTest(BaseProyeccionTest):

    def setUp(self):
        self.linea = self.crear_linea(self.proy_urg)
        self.proy_urg.estado = EstadoProyeccion.ENVIADA
        self.proy_urg.save()

    def test_no_aprueba_con_autorizado_vacio(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:aprobar', args=[self.proy_urg.pk]))
        self.proy_urg.refresh_from_db()
        self.assertEqual(self.proy_urg.estado, EstadoProyeccion.ENVIADA)

    def test_aprueba_con_cero_autorizado(self):
        self.linea.cantidad_autorizada = 0
        self.linea.save()
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:aprobar', args=[self.proy_urg.pk]))
        self.proy_urg.refresh_from_db()
        self.assertEqual(self.proy_urg.estado, EstadoProyeccion.APROBADA)
        self.assertEqual(self.proy_urg.aprobada_por, self.admin)
        self.assertIsNotNone(self.proy_urg.fecha_aprobacion)

    def test_coordinador_no_aprueba(self):
        self.linea.cantidad_autorizada = 5
        self.linea.save()
        self.client.force_login(self.coord_urg)
        respuesta = self.client.post(reverse('proyecciones:aprobar', args=[self.proy_urg.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.proy_urg.refresh_from_db()
        self.assertEqual(self.proy_urg.estado, EstadoProyeccion.ENVIADA)
        
class ProductosSugeridosTest(BaseProyeccionTest):

    def test_formulario_ofrece_solo_productos_activos(self):
        ProductoSugerido.objects.create(nombre='Gasas esteriles')
        ProductoSugerido.objects.create(nombre='Producto viejo', activo=False)
        self.client.force_login(self.coord_urg)
        respuesta = self.client.get(reverse('proyecciones:agregar_linea', args=[self.proy_urg.pk]))
        self.assertContains(respuesta, 'Gasas esteriles')
        self.assertNotContains(respuesta, 'Producto viejo')
    
class CalculosLineaTest(BaseProyeccionTest):

    def test_total_anual_y_costo(self):
        linea = self.crear_linea(self.proy_urg)
        linea.ene = 10
        linea.feb = 5
        linea.precio_unitario_est = 1000
        linea.save()
        linea.refresh_from_db()
        self.assertEqual(linea.total_anual, linea.ene + linea.feb + sum(getattr(linea, m) for m in Linea.MESES[2:]))
        self.assertEqual(linea.costo, linea.total_anual * linea.precio_unitario_est)
        
class BorrarLineaTest(BaseProyeccionTest):

    def test_coordinador_borra_su_linea_en_borrador(self):
        linea = self.crear_linea(self.proy_urg)
        self.client.force_login(self.coord_urg)
        self.client.post(reverse('proyecciones:borrar_linea', args=[linea.pk]))
        self.assertFalse(Linea.objects.filter(pk=linea.pk).exists())

    def test_coordinador_no_borra_linea_de_otra_area(self):
        linea = self.crear_linea(self.proy_urg)
        self.client.force_login(self.coord_lab)
        self.client.post(reverse('proyecciones:borrar_linea', args=[linea.pk]))
        self.assertTrue(Linea.objects.filter(pk=linea.pk).exists())
        
class AbrirPeriodoTest(BaseProyeccionTest):

    def datos(self, anio):
        return {'anio': anio, 'fecha_limite': date.today() + timedelta(days=30)}

    def test_crea_borradores_solo_de_areas_activas(self):
        Area.objects.create(nombre='Cerrada', codigo_area='CER', activa=False)
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:abrir_periodo'), self.datos(2028))
        proyecciones = ProyeccionArea.objects.filter(periodo__anio=2028)
        self.assertEqual(proyecciones.count(), 2)  # Urgencias y Laboratorio, no la inactiva
        self.assertTrue(all(p.estado == EstadoProyeccion.BORRADOR for p in proyecciones))
        self.assertEqual(proyecciones.get(area=self.urgencias).responsable, self.coord_urg)

    def test_reabrir_solo_crea_lo_que_falta(self):
        self.crear_linea(self.proy_urg)  # 2027 ya tiene Urgencias con una línea
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:abrir_periodo'), self.datos(2027))
        self.assertEqual(ProyeccionArea.objects.filter(periodo=self.periodo).count(), 2)  # solo se agregó Laboratorio
        self.assertEqual(self.proy_urg.lineas.count(), 1)  # lo existente no se tocó

    def test_coordinador_no_abre_periodo(self):
        self.client.force_login(self.coord_urg)
        respuesta = self.client.get(reverse('proyecciones:abrir_periodo'))
        self.assertEqual(respuesta.status_code, 403)