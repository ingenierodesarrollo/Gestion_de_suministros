from datetime import date, timedelta

from django.urls import reverse

from .models import Ajuste, Bitacora, EstadoProyeccion, Linea, ProyeccionArea
from .tests import BaseProyeccionTest


def datos_formset(linea, autorizado):
    """Lo que envía la pantalla Revisar al guardar la cantidad autorizada de una línea."""
    return {
        'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '1',
        'form-MIN_NUM_FORMS': '0', 'form-MAX_NUM_FORMS': '1000',
        'form-0-id': linea.pk, 'form-0-cantidad_autorizada': autorizado,
    }


class FlujoCompletoTest(BaseProyeccionTest):
    """Recorre todo el proceso como lo haría la coordinadora con un área, de principio a fin."""

    def test_de_abrir_periodo_a_ajustar(self):
        # 1. El administrador abre el periodo 2030: se crea un borrador por cada área activa.
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:abrir_periodo'),
                         {'anio': 2030, 'fecha_limite': date.today() + timedelta(days=30)})
        proyeccion = ProyeccionArea.objects.get(periodo__anio=2030, area=self.urgencias)
        self.assertEqual(proyeccion.estado, EstadoProyeccion.BORRADOR)

        # 2. El coordinador de Urgencias agrega una línea y envía.
        self.client.force_login(self.coord_urg)
        datos = {'producto': 'Guantes', 'dependencia': '', 'serie': '', 'unidad': self.unidad.pk,
                 **{mes: 0 for mes in Linea.MESES}, 'ene': 10, 'precio_unitario_est': '1500'}
        self.client.post(reverse('proyecciones:agregar_linea', args=[proyeccion.pk]), datos)
        linea = proyeccion.lineas.get()
        self.client.post(reverse('proyecciones:enviar', args=[proyeccion.pk]))
        proyeccion.refresh_from_db()
        self.assertEqual(proyeccion.estado, EstadoProyeccion.ENVIADA)

        # 3. El administrador llena el autorizado y aprueba.
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:revisar', args=[proyeccion.pk]), datos_formset(linea, '8'))
        self.client.post(reverse('proyecciones:aprobar', args=[proyeccion.pk]))
        proyeccion.refresh_from_db()
        self.assertEqual(proyeccion.estado, EstadoProyeccion.APROBADA)
        self.assertEqual(proyeccion.aprobada_por, self.admin)

        # 4. Después de aprobar, el administrador ajusta el autorizado con justificación.
        datos.update({'cantidad_autorizada': '6', 'motivo': 'Presupuesto recortado'})
        self.client.post(reverse('proyecciones:corregir_linea', args=[linea.pk]), datos)
        linea.refresh_from_db()
        self.assertEqual(linea.cantidad_autorizada, 6)
        ajuste = Ajuste.objects.get(linea=linea)
        self.assertEqual((ajuste.valor_aprobado, ajuste.valor_nuevo), ('8', '6'))

        # 5. La bitácora tiene cada paso del proceso.
        acciones = set(Bitacora.objects.values_list('accion', flat=True))
        self.assertTrue({'abrir', 'crear', 'enviar', 'editar', 'aprobar', 'ajustar'} <= acciones)


class CorregirTest(BaseProyeccionTest):
    """Lo que el administrador cambia en una proyección ya enviada o aprobada."""

    def setUp(self):
        self.linea = self.crear_linea(self.proy_urg, cantidad_autorizada=5)
        self.client.force_login(self.admin)

    def _datos(self, **cambios):
        datos = {'producto': 'Guantes', 'dependencia': '', 'serie': '', 'unidad': self.unidad.pk,
                 **{mes: 0 for mes in Linea.MESES}, 'ene': 10, 'precio_unitario_est': '1500',
                 'cantidad_autorizada': '5', 'motivo': 'Error al digitar'}
        datos.update(cambios)
        return datos

    def _poner_estado(self, estado):
        self.proy_urg.estado = estado
        self.proy_urg.save()

    def test_corregir_enviada_cambia_y_deja_rastro(self):
        self._poner_estado(EstadoProyeccion.ENVIADA)
        self.client.post(reverse('proyecciones:corregir_linea', args=[self.linea.pk]), self._datos(ene=12))
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.ene, 12)
        fila = Bitacora.objects.get(accion='corregir', registro_id=self.linea.pk)
        self.assertEqual((fila.campo, fila.valor_anterior, fila.valor_nuevo, fila.motivo),
                         ('ene', '10', '12', 'Error al digitar'))
        self.assertFalse(Ajuste.objects.exists())  # antes de aprobar es corrección, no ajuste

    def test_corregir_sin_justificacion_no_cambia_nada(self):
        self._poner_estado(EstadoProyeccion.ENVIADA)
        respuesta = self.client.post(reverse('proyecciones:corregir_linea', args=[self.linea.pk]),
                                     self._datos(ene=12, motivo=''))
        self.assertEqual(respuesta.status_code, 200)  # vuelve al formulario con el error
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.ene, 10)
        self.assertFalse(Bitacora.objects.filter(accion='corregir').exists())

    def test_ajustar_sin_justificacion_no_cambia_nada(self):
        self._poner_estado(EstadoProyeccion.APROBADA)
        respuesta = self.client.post(reverse('proyecciones:corregir_linea', args=[self.linea.pk]),
                                     self._datos(cantidad_autorizada='3', motivo=''))
        self.assertEqual(respuesta.status_code, 200)
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.cantidad_autorizada, 5)
        self.assertFalse(Ajuste.objects.exists())


class CoordinadorNoCorrigeTest(BaseProyeccionTest):
    """Aunque escriba la dirección a mano, el coordinador no hace lo que es solo de administradores."""

    def setUp(self):
        self.linea = self.crear_linea(self.proy_urg)
        self.proy_urg.estado = EstadoProyeccion.ENVIADA
        self.proy_urg.save()
        self.client.force_login(self.coord_urg)

    def test_no_corrige_su_linea_enviada(self):
        url = reverse('proyecciones:corregir_linea', args=[self.linea.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        respuesta = self.client.post(url, {'producto': 'Cambiado', 'motivo': 'Intento'})
        self.assertEqual(respuesta.status_code, 403)
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.producto, 'Guantes')

    def test_no_guarda_autorizado(self):
        respuesta = self.client.post(reverse('proyecciones:revisar', args=[self.proy_urg.pk]),
                                     datos_formset(self.linea, '99'))
        self.assertEqual(respuesta.status_code, 403)
        self.linea.refresh_from_db()
        self.assertIsNone(self.linea.cantidad_autorizada)


class NumerosNegativosTest(BaseProyeccionTest):
    """Cantidades, precios y autorizados negativos se rechazan."""

    def _datos(self, **cambios):
        datos = {'producto': 'Guantes', 'dependencia': '', 'serie': '', 'unidad': self.unidad.pk,
                 **{mes: 0 for mes in Linea.MESES}, 'ene': 10, 'precio_unitario_est': '1500'}
        datos.update(cambios)
        return datos

    def test_cantidad_negativa_no_se_guarda(self):
        self.client.force_login(self.coord_urg)
        self.client.post(reverse('proyecciones:agregar_linea', args=[self.proy_urg.pk]), self._datos(feb=-5))
        self.assertFalse(self.proy_urg.lineas.exists())

    def test_precio_negativo_no_se_guarda(self):
        self.client.force_login(self.coord_urg)
        self.client.post(reverse('proyecciones:agregar_linea', args=[self.proy_urg.pk]),
                         self._datos(precio_unitario_est='-100'))
        self.assertFalse(self.proy_urg.lineas.exists())

    def test_autorizado_negativo_no_se_guarda(self):
        linea = self.crear_linea(self.proy_urg)
        self.proy_urg.estado = EstadoProyeccion.ENVIADA
        self.proy_urg.save()
        self.client.force_login(self.admin)
        self.client.post(reverse('proyecciones:revisar', args=[self.proy_urg.pk]), datos_formset(linea, '-3'))
        linea.refresh_from_db()
        self.assertIsNone(linea.cantidad_autorizada)
