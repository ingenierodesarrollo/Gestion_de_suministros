from datetime import date

from django.test import TestCase
from django.urls import reverse

from areas.models import Area
from cuentas.models import Rol, Usuario
from proveedores.models import Categoria, Proveedor
from proyecciones.models import Periodo, ProyeccionArea


CLAVE = 'Clave-Segura-2027'


class CoordinadoresAreaTest(TestCase):
    def setUp(self):
        self.urgencias = Area.objects.create(nombre='Urgencias', codigo_area='URG')
        self.laboratorio = Area.objects.create(nombre='Laboratorio', codigo_area='LAB')
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Administrador', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.client.force_login(self.admin)

    def coordinador(self, correo, nombre, area=None, activo=True):
        return Usuario.objects.create_user(
            correo, nombre, password=CLAVE, rol=Rol.COORDINADOR, area=area, activo=activo)

    def datos_area(self, area, coordinadores=()):
        return {
            'nombre': area.nombre,
            'codigo_area': area.codigo_area,
            'activa': 'on',
            'coordinadores': [usuario.pk for usuario in coordinadores],
        }

    def test_asigna_un_coordinador_sin_area(self):
        coordinador = self.coordinador('nuevo@ejemplo.test', 'Coordinador Nuevo')
        respuesta = self.client.post(
            reverse('configuracion:area_editar', args=[self.urgencias.pk]),
            self.datos_area(self.urgencias, [coordinador]),
        )
        self.assertRedirects(respuesta, reverse('configuracion:areas'))
        coordinador.refresh_from_db()
        self.assertEqual(coordinador.area, self.urgencias)

    def test_mueve_un_coordinador_desde_otra_area(self):
        coordinador = self.coordinador('movido@ejemplo.test', 'Coordinador Movido', self.urgencias)
        self.client.post(
            reverse('configuracion:area_editar', args=[self.laboratorio.pk]),
            self.datos_area(self.laboratorio, [coordinador]),
        )
        coordinador.refresh_from_db()
        self.assertEqual(coordinador.area, self.laboratorio)

    def test_solo_ofrece_coordinadores_activos(self):
        disponible = self.coordinador('coord@ejemplo.test', 'Coordinador Activo')
        inactivo = self.coordinador('inactivo@ejemplo.test', 'Coordinador Inactivo', activo=False)
        desarrollador = Usuario.objects.create_user(
            'dev@ejemplo.test', 'Desarrollador', password=CLAVE, rol=Rol.DESARROLLADOR)
        categoria = Categoria.objects.create(nombre='Categoría ficticia')
        proveedor = Proveedor.objects.create(
            nit='900123456-7', razon_social='Proveedor Ficticio SAS',
            tipo_persona='juridica', categoria=categoria,
        )
        usuario_proveedor = Usuario.objects.create_user(
            'proveedor@ejemplo.test', 'Proveedor', password=CLAVE,
            rol=Rol.PROVEEDOR, proveedor=proveedor,
        )

        respuesta = self.client.get(reverse('configuracion:area_nueva'))
        opciones = respuesta.context['form'].fields['coordinadores'].queryset
        self.assertQuerySetEqual(opciones, [disponible])
        for usuario in (self.admin, desarrollador, usuario_proveedor, inactivo):
            self.assertNotIn(usuario, opciones)

    def test_indica_si_el_coordinador_esta_en_otra_area(self):
        coordinador = self.coordinador('coord@ejemplo.test', 'Coordinador Actual', self.urgencias)
        respuesta = self.client.get(reverse('configuracion:area_editar', args=[self.laboratorio.pk]))
        self.assertContains(
            respuesta,
            f'Coordinador Actual &lt;{coordinador.correo}&gt; (hoy en URG - Urgencias)',
        )

    def test_marca_los_coordinadores_que_ya_pertenecen_al_area(self):
        coordinador = self.coordinador('coord@ejemplo.test', 'Coordinador Actual', self.urgencias)
        respuesta = self.client.get(reverse('configuracion:area_editar', args=[self.urgencias.pk]))
        iniciales = respuesta.context['form'].initial['coordinadores']
        self.assertQuerySetEqual(iniciales, [coordinador])

    def test_no_deja_un_coordinador_activo_sin_area(self):
        coordinador = self.coordinador('coord@ejemplo.test', 'Coordinador Actual', self.urgencias)
        respuesta = self.client.post(
            reverse('configuracion:area_editar', args=[self.urgencias.pk]),
            self.datos_area(self.urgencias),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            'Para quitar a Coordinador Actual de esta área, asígnelo a otra área o desactívelo desde Usuarios.',
        )
        coordinador.refresh_from_db()
        self.assertEqual(coordinador.area, self.urgencias)

    def test_lista_muestra_los_coordinadores(self):
        self.coordinador('ana@ejemplo.test', 'Ana', self.urgencias)
        self.coordinador('beatriz@ejemplo.test', 'Beatriz', self.urgencias)
        respuesta = self.client.get(reverse('configuracion:areas'))
        self.assertContains(respuesta, 'Ana, Beatriz')
        self.assertContains(respuesta, 'Sin coordinador')

    def test_coordinador_y_proveedor_no_entran(self):
        coordinador = self.coordinador('coord@ejemplo.test', 'Coordinador', self.urgencias)
        categoria = Categoria.objects.create(nombre='Categoría ficticia')
        proveedor = Proveedor.objects.create(
            nit='900123456-7', razon_social='Proveedor Ficticio SAS',
            tipo_persona='juridica', categoria=categoria,
        )
        usuario_proveedor = Usuario.objects.create_user(
            'proveedor@ejemplo.test', 'Proveedor', password=CLAVE,
            rol=Rol.PROVEEDOR, proveedor=proveedor,
        )
        for usuario in (coordinador, usuario_proveedor):
            self.client.force_login(usuario)
            for nombre, args in (
                ('areas', []), ('area_nueva', []), ('area_editar', [self.urgencias.pk]),
            ):
                with self.subTest(usuario=usuario.rol, vista=nombre):
                    respuesta = self.client.get(reverse(f'configuracion:{nombre}', args=args))
                    self.assertEqual(respuesta.status_code, 403)

    def test_el_coordinador_movido_ve_la_proyeccion_de_su_nueva_area(self):
        coordinador = self.coordinador('coord@ejemplo.test', 'Coordinador', self.urgencias)
        periodo = Periodo.objects.create(
            anio=2031, fecha_apertura=date(2030, 10, 1), fecha_limite=date(2030, 12, 15),
            abierto_por=self.admin,
        )
        anterior = ProyeccionArea.objects.create(
            periodo=periodo, area=self.urgencias, responsable=coordinador)
        nueva = ProyeccionArea.objects.create(
            periodo=periodo, area=self.laboratorio, responsable=coordinador)
        self.client.post(
            reverse('configuracion:area_editar', args=[self.laboratorio.pk]),
            self.datos_area(self.laboratorio, [coordinador]),
        )

        self.client.force_login(coordinador)
        respuesta = self.client.get(reverse('proyecciones:mi_proyeccion'))
        proyecciones = list(respuesta.context['proyecciones'])
        self.assertIn(nueva, proyecciones)
        self.assertNotIn(anterior, proyecciones)
