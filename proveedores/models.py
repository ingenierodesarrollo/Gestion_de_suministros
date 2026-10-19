from datetime import timedelta


from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone



class Categoria(models.Model):
    """Las 11 categorías de proveedor del FR-GDS-14 (Lavandería, Proveedores generales...)."""
    nombre = models.CharField(max_length=100, unique=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"

    def __str__(self):
        return self.nombre


class Requisito(models.Model):
    """Los 26 requisitos (preguntas) del FR-GDS-14."""
    BLOQUES = [
        ("calidad", "Calidad"),
        ("ambiental", "Ambiental"),
        ("sgsst", "SG-SST"),
    ]
    numero = models.PositiveSmallIntegerField(unique=True)
    bloque = models.CharField(max_length=10, choices=BLOQUES)
    texto = models.CharField(max_length=300)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"{self.numero}. {self.texto}"


class Peso(models.Model):
    """La hoja oculta M_pesos: cuánto vale cada requisito según la categoría (1 o 2)."""
    requisito = models.ForeignKey(Requisito, on_delete=models.CASCADE, related_name="pesos")
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="pesos")
    valor = models.PositiveSmallIntegerField(choices=[(1, "1"), (2, "2")])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requisito", "categoria"], name="peso_unico_por_categoria"),
        ]

    def __str__(self):
        return f"{self.requisito.numero} / {self.categoria}: {self.valor}"
    
DIAS_AVISO_VENCIMIENTO = 30


class Proveedor(models.Model):
    """La ficha del proveedor. El NIT es la llave: no puede repetirse."""
    TIPOS_PERSONA = [
        ("natural", "Persona natural"),
        ("juridica", "Persona jurídica"),
    ]
    ESTADOS = [
        ("en_revision", "En revisión"),
        ("aprobado", "Aprobado"),
        ("condicionado", "Condicionado"),
        ("bloqueado", "Bloqueado"),
    ]
    nit = models.CharField(
        "NIT", max_length=20, unique=True,
        validators=[RegexValidator(r"^\d{6,12}(-\d)?$", "Escribe el NIT solo con números y, si quieres, el dígito de verificación: 900123456-7")],
    )
    razon_social = models.CharField("razón social", max_length=200)
    tipo_persona = models.CharField(max_length=10, choices=TIPOS_PERSONA)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="proveedores")
    contacto_nombre = models.CharField("nombre de contacto", max_length=120, blank=True)
    contacto_correo = models.EmailField("correo de contacto", blank=True)
    contacto_telefono = models.CharField("teléfono de contacto", max_length=30, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default="en_revision")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["razon_social"]
        verbose_name_plural = "proveedores"

    def __str__(self):
        return f"{self.razon_social} ({self.nit})"


class TipoDocumento(models.Model):
    """Cada documento que se le pide a un proveedor y cada cuánto vence."""
    nombre = models.CharField(max_length=150, unique=True)
    vence = models.BooleanField(default=True)
    vigencia_dias = models.PositiveSmallIntegerField(
        "vigencia en días", null=True, blank=True,
        help_text="Ej. 30, 90 o 365. Déjalo vacío si la fecha la trae el propio documento.",
    )
    requisito = models.ForeignKey(
        Requisito, on_delete=models.SET_NULL, null=True, blank=True, related_name="tipos_documento",
        help_text="Requisito del FR-GDS-14 al que corresponde, si aplica.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tipo de documento"
        verbose_name_plural = "tipos de documento"

    def __str__(self):
        return self.nombre


class DocumentoProveedor(models.Model):
    """Un documento de un proveedor. El archivo vive en Drive; aquí solo va el enlace."""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT, related_name="documentos")
    fecha_expedicion = models.DateField("fecha de expedición", null=True, blank=True)
    fecha_vencimiento = models.DateField("fecha de vencimiento", null=True, blank=True)
    enlace_drive = models.URLField("enlace a Drive", max_length=500)
    observaciones = models.CharField(max_length=300, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_vencimiento"]
        verbose_name = "documento de proveedor"
        verbose_name_plural = "documentos de proveedores"

    def __str__(self):
        return f"{self.tipo} · {self.proveedor.razon_social}"

    def clean(self):
        if self.tipo_id and self.tipo.vence and not self.fecha_vencimiento:
            raise ValidationError({"fecha_vencimiento": "Este tipo de documento vence: escribe la fecha de vencimiento."})
        if self.fecha_expedicion and self.fecha_vencimiento and self.fecha_vencimiento < self.fecha_expedicion:
            raise ValidationError({"fecha_vencimiento": "El vencimiento no puede ser anterior a la expedición."})

    def estado_vigencia(self, hoy=None):
        """Devuelve 'sin_vencimiento', 'vigente', 'por_vencer' o 'vencido'."""
        if not self.fecha_vencimiento:
            return "sin_vencimiento"
        hoy = hoy or timezone.localdate()
        if self.fecha_vencimiento < hoy:
            return "vencido"
        if self.fecha_vencimiento <= hoy + timedelta(days=DIAS_AVISO_VENCIMIENTO):
            return "por_vencer"
        return "vigente"    