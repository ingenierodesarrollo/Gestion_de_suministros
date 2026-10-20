from datetime import timedelta

from django import forms
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import DocumentoProveedor, Proveedor


class ProcesarEnvioForm(forms.ModelForm):
    """La coordinadora vincula el envío a un proveedor y registra el documento con su vencimiento."""

    class Meta:
        model = DocumentoProveedor
        fields = ["proveedor", "fecha_expedicion", "fecha_vencimiento", "observaciones"]
        widgets = {
            "fecha_expedicion": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, envio, **kwargs):
        self.envio = envio
        super().__init__(*args, **kwargs)
        # El documento nace con el tipo y el archivo que envió el proveedor.
        self.instance.tipo = envio.tipo
        self.instance.archivo = envio.archivo
        self.fields["proveedor"].queryset = Proveedor.objects.all()
        self.fields["proveedor"].empty_label = "Seleccione el proveedor"
        # Si el envío ya trae proveedor (portal) o hay uno con ese NIT, viene preseleccionado.
        sugerido = envio.proveedor or envio.proveedor_sugerido()
        if sugerido:
            self.fields["proveedor"].initial = sugerido.pk
        self.fields["fecha_vencimiento"].help_text = (
            "Obligatoria si este documento vence." if envio.tipo.vence else "Este documento no vence: déjela vacía."
        )
        if envio.tipo.vigencia_dias:
            self.fields["fecha_vencimiento"].help_text += f" Si la deja vacía, se calcula con la expedición + {envio.tipo.vigencia_dias} días."

    def clean(self):
        datos = super().clean()
        tipo = self.envio.tipo
        if tipo.vigencia_dias and datos.get("fecha_expedicion") and not datos.get("fecha_vencimiento"):
            datos["fecha_vencimiento"] = datos["fecha_expedicion"] + timedelta(days=tipo.vigencia_dias)
        return datos

    def guardar(self, usuario):
        """Crea el documento con su propia copia del PDF y marca el envío como procesado."""
        documento = self.instance
        envio = self.envio
        with envio.archivo.open("rb") as origen:
            documento.archivo = None  # se reemplaza por la copia
            documento.archivo.save("documento.pdf", ContentFile(origen.read()), save=False)
        documento.registrado_por = usuario
        documento.save()
        envio.estado = "procesado"
        envio.proveedor = documento.proveedor
        envio.documento = documento
        envio.revisado_por = usuario
        envio.fecha_revision = timezone.now()
        envio.save()
        return documento


class DescartarEnvioForm(forms.Form):
    motivo = forms.CharField(
        label="¿Por qué se descarta?", max_length=300,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="El proveedor verá este motivo en su portal.",
    )
