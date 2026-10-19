from django.test import TestCase

from proveedores.models import Requisito, TipoDocumento


class TiposDocumentoInicialesTests(TestCase):
    """Comprueba que la migración 0004 cargó la lista inicial de tipos de documento."""

    def test_cantidad(self):
        self.assertEqual(TipoDocumento.objects.count(), 28)

    def test_cada_requisito_documento_tiene_un_tipo(self):
        # El requisito 16 (ficha de cotización) es de cada compra, no del proveedor.
        con_tipo = set(TipoDocumento.objects.exclude(requisito=None).values_list("requisito__numero", flat=True))
        esperados = set(Requisito.objects.values_list("numero", flat=True)) - {16}
        self.assertEqual(con_tipo, esperados)

    def test_no_hay_dos_tipos_para_el_mismo_requisito(self):
        numeros = list(TipoDocumento.objects.exclude(requisito=None).values_list("requisito__numero", flat=True))
        self.assertEqual(len(numeros), len(set(numeros)))

    def test_vigencias_conocidas(self):
        self.assertEqual(TipoDocumento.objects.get(nombre="Planilla de seguridad social").vigencia_dias, 30)
        self.assertEqual(TipoDocumento.objects.get(nombre="Certificado de Cámara de Comercio").vigencia_dias, 90)
        self.assertFalse(TipoDocumento.objects.get(nombre="RUT").vence)

    def test_tipos_sin_requisito(self):
        sin_requisito = set(TipoDocumento.objects.filter(requisito=None).values_list("nombre", flat=True))
        self.assertEqual(sin_requisito, {"SICOF", "Contrato", "Póliza"})

    def test_si_no_vence_no_tiene_vigencia(self):
        self.assertFalse(TipoDocumento.objects.filter(vence=False).exclude(vigencia_dias=None).exists())
