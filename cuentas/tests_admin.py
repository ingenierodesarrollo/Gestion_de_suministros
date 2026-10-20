import shutil
import tempfile

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from areas.models import Area
from cuentas.models import Rol, Usuario
from proveedores.models import Categoria, EnvioProveedor, Proveedor, TipoDocumento
from proyecciones.models import AccionBitacora, Bitacora

CLAVE = 'Clave-Segura-2027'
CARPETA_PRUEBAS = tempfile.mkdtemp()


class AdminPorRolTest(TestCase):
    """Quién entra al panel /admin/ ("Opciones avanzadas") y qué puede hacer allí."""

    def setUp(self):
        area = Area.objects.create(nombre='Urgencias', codigo_area='URG')
        self.coord = Usuario.objects.create_user(
            'coord@ejemplo.test', 'Coord', password=CLAVE, rol=Rol.COORDINADOR, area=area)
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.dev_sin_superusuario = Usuario.objects.create_user(
            'dev2@ejemplo.test', 'Dev dos', password=CLAVE, rol=Rol.DESARROLLADOR)
        self.dev = Usuario.objects.create_superuser('dev@ejemplo.test', 'Dev', password=CLAVE)
        self.registro = Bitacora.objects.create(
            usuario=self.admin, accion=AccionBitacora.choices[0][0], tabla='linea', registro_id=1)

    def test_administradores_y_desarrolladores_entran_sin_ser_superusuarios(self):
        self.assertFalse(self.admin.is_superuser)
        for usuario in (self.admin, self.dev_sin_superusuario, self.dev):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get('/admin/').status_code, 200)
            self.assertEqual(self.client.get('/admin/areas/area/').status_code, 200)

    def test_coordinador_de_area_no_entra(self):
        self.assertFalse(self.coord.is_staff)
        self.assertFalse(self.coord.has_perm('areas.change_area'))
        self.assertFalse(self.coord.has_module_perms('areas'))
        self.client.force_login(self.coord)
        respuesta = self.client.get('/admin/')
        self.assertEqual(respuesta.status_code, 302)  # lo manda al ingreso del panel
        self.assertEqual(self.client.get('/admin/areas/area/').status_code, 302)

    def test_administrador_puede_todo_menos_tocar_el_historial(self):
        self.assertTrue(self.admin.has_perm('areas.change_area'))
        self.assertTrue(self.admin.has_perm('proveedores.add_proveedor'))
        for modelo in ('bitacora', 'ajuste'):
            self.assertTrue(self.admin.has_perm(f'proyecciones.view_{modelo}'))
            for accion in ('add', 'change', 'delete'):
                self.assertFalse(self.admin.has_perm(f'proyecciones.{accion}_{modelo}'))

    def test_administrador_ve_la_bitacora_pero_no_la_cambia_ni_la_borra(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/proyecciones/bitacora/').status_code, 200)
        self.assertEqual(self.client.get('/admin/proyecciones/bitacora/add/').status_code, 403)
        self.assertEqual(self.client.get(f'/admin/proyecciones/bitacora/{self.registro.pk}/delete/').status_code, 403)
        detalle = self.client.get(f'/admin/proyecciones/bitacora/{self.registro.pk}/change/')
        self.assertEqual(detalle.status_code, 200)
        self.assertNotContains(detalle, 'name="_save"')
        self.client.post(f'/admin/proyecciones/bitacora/{self.registro.pk}/change/', {'tabla': 'otra'})
        self.registro.refresh_from_db()
        self.assertEqual(self.registro.tabla, 'linea')

    def test_lo_tecnico_solo_lo_ven_los_desarrolladores(self):
        self.assertFalse(self.admin.has_module_perms('axes'))
        self.client.force_login(self.admin)
        inicio = self.client.get('/admin/')
        self.assertNotContains(inicio, '/admin/axes/')
        self.assertNotContains(inicio, '/admin/auth/group/')  # los grupos ya no se usan
        self.client.force_login(self.dev)
        self.assertContains(self.client.get('/admin/'), '/admin/axes/')

    def test_administrador_no_ve_la_casilla_de_superusuario(self):
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(f'/admin/cuentas/usuario/{self.coord.pk}/change/'), 'is_superuser')
        self.client.force_login(self.dev)
        self.assertContains(self.client.get(f'/admin/cuentas/usuario/{self.coord.pk}/change/'), 'is_superuser')

    def test_todas_las_pantallas_del_panel_abren(self):
        """Lista y formulario nuevo de cada tabla del panel abren sin errores."""
        for usuario in (self.admin, self.dev):
            self.client.force_login(usuario)
            for modelo in admin.site._registry:
                opciones = modelo._meta
                if opciones.app_label == 'axes' and usuario == self.admin:
                    continue
                lista = reverse(f'admin:{opciones.app_label}_{opciones.model_name}_changelist')
                self.assertEqual(self.client.get(lista).status_code, 200, lista)
                if usuario.has_perm(f'{opciones.app_label}.add_{opciones.model_name}'):
                    nuevo = reverse(f'admin:{opciones.app_label}_{opciones.model_name}_add')
                    self.assertIn(self.client.get(nuevo).status_code, (200, 403), nuevo)


class BotonOpcionesAvanzadasTest(TestCase):
    def setUp(self):
        area = Area.objects.create(nombre='Urgencias', codigo_area='URG')
        self.coord = Usuario.objects.create_user(
            'coord@ejemplo.test', 'Coord', password=CLAVE, rol=Rol.COORDINADOR, area=area)
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.dev = Usuario.objects.create_superuser('dev@ejemplo.test', 'Dev', password=CLAVE)

    def test_solo_lo_ve_quien_tiene_acceso_al_panel(self):
        for pagina in (reverse('inicio'), reverse('cambiar_clave')):
            self.client.force_login(self.coord)
            self.assertNotContains(self.client.get(pagina), 'Opciones avanzadas')
            for usuario in (self.admin, self.dev):
                self.client.force_login(usuario)
                self.assertContains(self.client.get(pagina), 'Opciones avanzadas')

    def test_barra_con_desplegables_proyecciones_y_configuracion(self):
        self.client.force_login(self.admin)
        pagina = self.client.get(reverse('proyecciones:revision'))
        self.assertContains(pagina, '<summary class="activo">Proyecciones</summary>', html=False)
        self.assertContains(pagina, 'Configuración</summary>')
        for nombre in ('proyecciones:abrir_periodo', 'proyecciones:bitacora', 'configuracion:areas',
                       'configuracion:unidades', 'configuracion:productos', 'configuracion:usuarios'):
            self.assertContains(pagina, reverse(nombre))
        self.client.force_login(self.coord)
        self.assertNotContains(self.client.get(reverse('cambiar_clave')), 'Configuración</summary>')


PDF = b"%PDF-1.4\n% documento inventado para pruebas\n"


@override_settings(MEDIA_ROOT=CARPETA_PRUEBAS)
class EnviosEnElPanelTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(CARPETA_PRUEBAS, ignore_errors=True)

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.rut = TipoDocumento.objects.get(nombre='RUT')
        self.envio = EnvioProveedor.objects.create(
            nit='900123456-7', razon_social='Proveedor Ficticio SAS', tipo=self.rut,
            archivo=SimpleUploadedFile('rut.pdf', PDF, content_type='application/pdf'))
        self.client.force_login(self.admin)

    def test_un_envio_guardado_solo_se_ve(self):
        url = f'/admin/proveedores/envioproveedor/{self.envio.pk}/change/'
        pagina = self.client.get(url)
        self.assertEqual(pagina.status_code, 200)
        self.assertNotContains(pagina, 'name="_save"')
        self.assertNotContains(pagina, '/archivos/envios/')  # el archivo es privado: sin enlace
        self.client.post(url, {'nit': '111111111', 'estado': 'procesado'})
        self.envio.refresh_from_db()
        self.assertEqual(self.envio.nit, '900123456-7')
        self.assertEqual(self.envio.estado, 'pendiente')

    def test_sugiere_el_proveedor_por_nit(self):
        categoria = Categoria.objects.get(nombre='Proveedores Generales')
        Proveedor.objects.create(nit='900123456-7', razon_social='Proveedor Ficticio SAS',
                                 tipo_persona='juridica', categoria=categoria)
        pagina = self.client.get('/admin/proveedores/envioproveedor/')
        self.assertContains(pagina, 'Proveedor Ficticio SAS (900123456-7)')

    def test_registro_manual_queda_pendiente_y_manual(self):
        respuesta = self.client.post('/admin/proveedores/envioproveedor/add/', {
            'nit': '800111222', 'razon_social': 'Otro Ficticio SAS', 'tipo': self.rut.pk,
            'archivo': SimpleUploadedFile('otro.pdf', PDF, content_type='application/pdf'),
        })
        self.assertEqual(respuesta.status_code, 302)
        nuevo = EnvioProveedor.objects.get(nit='800111222')
        self.assertEqual((nuevo.estado, nuevo.origen), ('pendiente', 'manual'))


class BotonVolverTest(TestCase):
    def test_el_panel_tiene_boton_para_volver_a_proyecciones(self):
        admin_user = Usuario.objects.create_user(
            'admin@ejemplo.test', 'Admin', password=CLAVE, rol=Rol.ADMINISTRADOR)
        self.client.force_login(admin_user)
        for url in ('/admin/', '/admin/areas/area/'):
            self.assertContains(self.client.get(url), reverse('proyecciones:revision'))
            self.assertContains(self.client.get(url), 'Volver a Proyecciones')
