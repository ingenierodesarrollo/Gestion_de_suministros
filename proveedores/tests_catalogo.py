from django.test import TestCase

from proveedores.models import Categoria, Peso, Requisito


class CatalogoFRGDS14Tests(TestCase):
    """Comprueba que la migración 0002 cargó bien lo que dice el Excel FR-GDS-14."""

    def test_cantidades(self):
        self.assertEqual(Categoria.objects.count(), 11)
        self.assertEqual(Requisito.objects.count(), 26)
        self.assertEqual(Peso.objects.count(), 26 * 11)

    def test_bloques(self):
        self.assertEqual(Requisito.objects.filter(bloque="calidad").count(), 18)
        self.assertEqual(Requisito.objects.filter(bloque="ambiental").count(), 3)
        self.assertEqual(Requisito.objects.filter(bloque="sgsst").count(), 5)

    def test_todo_peso_es_1_o_2(self):
        self.assertFalse(Peso.objects.exclude(valor__in=[1, 2]).exists())

    def test_cada_requisito_tiene_un_peso_por_categoria(self):
        for requisito in Requisito.objects.all():
            self.assertEqual(requisito.pesos.count(), 11, requisito.numero)

    def test_maximo_de_proveedores_generales_es_37(self):
        # Es el total que da el Excel con todo aplicable para "Proveedores Generales".
        generales = Categoria.objects.get(nombre="Proveedores Generales")
        total = sum(p.valor for p in Peso.objects.filter(categoria=generales))
        self.assertEqual(total, 37)

    def test_invima_pesa_2_solo_en_ciertas_categorias(self):
        invima = Requisito.objects.get(numero=10)
        farmaceutico = Categoria.objects.get(nombre__startswith="Proveedor de Servicio Farmaceutico")
        generales = Categoria.objects.get(nombre="Proveedores Generales")
        self.assertEqual(Peso.objects.get(requisito=invima, categoria=farmaceutico).valor, 2)
        self.assertEqual(Peso.objects.get(requisito=invima, categoria=generales).valor, 1)
