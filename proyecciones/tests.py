from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from areas.models import Area
from cuentas.models import Rol, Usuario

from .models import EstadoProyeccion, Linea, Periodo, ProductoSugerido, ProyeccionArea, UnidadMedida, Bitacora, EstadoPeriodo


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
        
class PeriodoCerradoTest(BaseProyeccionTest):

    def test_con_periodo_cerrado_el_area_no_agrega_ni_edita_ni_envia(self):
        linea = self.crear_linea(self.proy_urg)
        self.periodo.estado = EstadoPeriodo.CERRADO
        self.periodo.save()
        self.client.force_login(self.coord_urg)
        self.assertEqual(self.client.get(reverse('proyecciones:agregar_linea', args=[self.proy_urg.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('proyecciones:editar_linea', args=[linea.pk]), {'producto': 'Cambiado'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('proyecciones:enviar', args=[self.proy_urg.pk])).status_code, 403)
        self.proy_urg.refresh_from_db()
        self.assertEqual(self.proy_urg.estado, EstadoProyeccion.BORRADOR)

    def test_administrador_cierra_y_reabre_con_rastro(self):
        self.client.force_login(self.admin)
        url = reverse('proyecciones:alternar_periodo', args=[self.periodo.pk])
        self.client.post(url)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, EstadoPeriodo.CERRADO)
        self.client.post(url)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, EstadoPeriodo.ABIERTO)
        self.assertEqual(Bitacora.objects.filter(tabla='periodo', registro_id=self.periodo.pk).count(), 2)

    def test_coordinador_no_cierra_periodo(self):
        self.client.force_login(self.coord_urg)
        respuesta = self.client.post(reverse('proyecciones:alternar_periodo', args=[self.periodo.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, EstadoPeriodo.ABIERTO)
        
class BitacoraTest(BaseProyeccionTest):

    def test_crear_editar_y_borrar_linea_dejan_rastro(self):
        self.client.force_login(self.coord_urg)
        datos = {'producto': 'Guantes', 'dependencia': '', 'serie': '', 'unidad': self.unidad.pk,
                 **{mes: 0 for mes in Linea.MESES}, 'precio_unitario_est': '1500'}
        self.client.post(reverse('proyecciones:agregar_linea', args=[self.proy_urg.pk]), datos)
        linea = self.proy_urg.lineas.get()
        self.assertTrue(Bitacora.objects.filter(accion='crear', registro_id=linea.pk).exists())
        datos['ene'] = 7
        self.client.post(reverse('proyecciones:editar_linea', args=[linea.pk]), datos)
        fila = Bitacora.objects.get(accion='editar', registro_id=linea.pk)
        self.assertEqual((fila.campo, fila.valor_anterior, fila.valor_nuevo), ('ene', '0', '7'))
        self.client.post(reverse('proyecciones:borrar_linea', args=[linea.pk]))
        self.assertTrue(Bitacora.objects.filter(accion='borrar', registro_id=linea.pk).exists())

    def test_enviar_y_aprobar_dejan_rastro(self):
        self.crear_linea(self.proy_urg, cantidad_autorizada=0)
        self.client.force_login(self.coord_urg)
        self.client.post(reverse('proyecciones:enviar', args=[self.proy_urg.pk]))
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:aprobar', args=[self.proy_urg.pk]))
        for accion in ('enviar', 'aprobar'):
            self.assertTrue(Bitacora.objects.filter(accion=accion, tabla='proyeccionarea', registro_id=self.proy_urg.pk).exists())

    def test_abrir_periodo_deja_rastro(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:abrir_periodo'), {'anio': 2030, 'fecha_limite': date.today() + timedelta(days=30)})
        periodo = Periodo.objects.get(anio=2030)
        fila = Bitacora.objects.get(accion='abrir', tabla='periodo', registro_id=periodo.pk)
        self.assertEqual(fila.valor_nuevo, '2')  # Urgencias y Laboratorio

    def test_guardar_autorizado_deja_rastro(self):
        linea = self.crear_linea(self.proy_urg)
        self.proy_urg.estado = EstadoProyeccion.ENVIADA
        self.proy_urg.save()
        self.client.force_login(self.admin)
        datos = {
            'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '0', 'form-MAX_NUM_FORMS': '1000',
            'form-0-id': linea.pk, 'form-0-cantidad_autorizada': '5',
        }
        self.client.post(reverse('proyecciones:revisar', args=[self.proy_urg.pk]), datos)
        fila = Bitacora.objects.get(accion='editar', registro_id=linea.pk)
        self.assertEqual((fila.campo, fila.valor_anterior, fila.valor_nuevo), ('cantidad_autorizada', '', '5'))
    
    def test_pantalla_bitacora_la_ve_el_admin_con_nombres_legibles(self):
        self.crear_linea(self.proy_urg, cantidad_autorizada=0)
        self.client.force_login(self.coord_urg)
        self.client.force_login(self.coord_urg)
        self.client.post(reverse('proyecciones:enviar', args=[self.proy_urg.pk]))
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('proyecciones:bitacora'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'Proyección {self.proy_urg.area.nombre}')

    def test_coordinador_no_ve_la_bitacora(self):
        self.client.force_login(self.coord_urg)
        respuesta = self.client.get(reverse('proyecciones:bitacora'))
        self.assertEqual(respuesta.status_code, 403)
        
class ObservacionesPequenasTest(BaseProyeccionTest):

    def _datos_linea(self, **cambios):
        datos = {'producto': 'Guantes', 'dependencia': '', 'serie': '', 'unidad': self.unidad.pk,
                 'precio_unitario_est': '1500', 'cantidad_autorizada': '', 'motivo': 'Prueba'}
        datos.update({mes: 0 for mes in Linea.MESES})
        datos.update(cambios)
        return datos

    def test_ajustar_no_deja_el_autorizado_vacio(self):
        linea = self.crear_linea(self.proy_urg, cantidad_autorizada=5)
        self.proy_urg.estado = EstadoProyeccion.APROBADA
        self.proy_urg.save()
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('proyecciones:corregir_linea', args=[linea.pk]), self._datos_linea())
        self.assertEqual(respuesta.status_code, 200)  # vuelve al formulario con el error
        linea.refresh_from_db()
        self.assertEqual(linea.cantidad_autorizada, 5)

    def test_no_se_abre_un_periodo_cerrado(self):
        self.periodo.estado = EstadoPeriodo.CERRADO
        self.periodo.save()
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('proyecciones:abrir_periodo'),
                                     {'anio': 2027, 'fecha_limite': date.today() + timedelta(days=30)})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(ProyeccionArea.objects.filter(periodo=self.periodo).count(), 1)  # no se agregó Laboratorio

    def test_cancelar_del_administrador_vuelve_a_revision(self):
        linea = self.crear_linea(self.proy_urg)
        self.proy_urg.estado = EstadoProyeccion.ENVIADA
        self.proy_urg.save()
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('proyecciones:corregir_linea', args=[linea.pk]))
        self.assertContains(respuesta, reverse('proyecciones:revisar', args=[self.proy_urg.pk]))

    def test_detalle_del_administrador_vuelve_a_revision(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('proyecciones:detalle', args=[self.proy_urg.pk]))
        self.assertNotContains(respuesta, 'Volver a Mi proyección')
        self.assertContains(respuesta, reverse('proyecciones:revision'))