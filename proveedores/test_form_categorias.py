from django.test import TestCase

from .forms import ProveedorForm
from .models import Categoria, Proveedor


class CategoriasEnFichaTest(TestCase):
    def setUp(self):
        self.activa = Categoria.objects.get(nombre="Proveedores Generales")
        self.inactiva = Categoria.objects.get(nombre="Servicio de Lavanderia y Aseo")
        self.inactiva.activa = False
        self.inactiva.save()

    def opciones(self, form):
        return set(form.fields["categoria"].queryset)

    def activas(self):
        return set(Categoria.objects.filter(activa=True))

    def test_proveedor_nuevo_no_ofrece_inactivas(self):
        self.assertEqual(self.opciones(ProveedorForm()), self.activas())

    def test_al_editar_no_ofrece_inactivas_ajenas(self):
        p = Proveedor.objects.create(nit="900111222-3", razon_social="X SAS", tipo_persona="juridica", categoria=self.activa)
        self.assertEqual(self.opciones(ProveedorForm(instance=p)), self.activas())

    def test_al_editar_conserva_la_suya_aunque_este_inactiva(self):
        p = Proveedor.objects.create(nit="900111222-3", razon_social="X SAS", tipo_persona="juridica", categoria=self.inactiva)
        self.assertEqual(self.opciones(ProveedorForm(instance=p)), self.activas() | {self.inactiva})
