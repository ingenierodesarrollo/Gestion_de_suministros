from datetime import timedelta
from pathlib import Path
from uuid import uuid4



from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
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

TAMANO_MAXIMO_MB = 10


def validar_pdf(archivo):
    """Revisa que el archivo de verdad sea un PDF (no solo que termine en .pdf) y que no pese demasiado."""
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(f"El archivo pesa más de {TAMANO_MAXIMO_MB} MB.")
    archivo.seek(0)
    inicio = archivo.read(5)
    archivo.seek(0)
    if inicio != b"%PDF-":
        raise ValidationError("El archivo no es un PDF válido.")


def ruta_envio(instancia, nombre):
    """Guarda el archivo con un nombre al azar, en una carpeta por año y mes."""
    return f"envios/{timezone.localdate():%Y/%m}/{uuid4().hex}.pdf"


def ruta_documento(instancia, nombre):
    return f"documentos/{timezone.localdate():%Y/%m}/{uuid4().hex}.pdf"


VALIDADORES_PDF = [FileExtensionValidator(["pdf"], "Solo se aceptan archivos PDF."), validar_pdf]

def limpiar_nit(nit):
    """Quita espacios y puntos: ' 900.123.456-7 ' queda '900123456-7'."""
    return nit.replace(".", "").replace(" ", "").strip()


def nit_base(nit):
    """El NIT sin el dígito de verificación: '900123456-7' y '900123456' dan '900123456'."""
    return limpiar_nit(nit).split("-")[0]


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
    
    @classmethod
    def con_mismo_nit(cls, nit):
        """Los proveedores con ese NIT, lo escriban con o sin dígito de verificación."""
        base = nit_base(nit)
        if not base:
            return cls.objects.none()
        return cls.objects.filter(models.Q(nit=base) | models.Q(nit__startswith=f"{base}-"))

    def clean(self):
        # El NIT idéntico ya lo revisa unique=True; aquí se atrapa 900111222 contra 900111222-3.
        if self.nit and Proveedor.con_mismo_nit(self.nit).exclude(pk=self.pk).exclude(nit=self.nit).exists():
            raise ValidationError({"nit": "Ya hay un proveedor con ese NIT (con o sin dígito de verificación)."})


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
    """Un documento de un proveedor. El archivo se guarda en el sistema o, si es antiguo, queda el enlace a Drive."""
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT, related_name="documentos")
    fecha_expedicion = models.DateField("fecha de expedición", null=True, blank=True)
    fecha_vencimiento = models.DateField("fecha de vencimiento", null=True, blank=True)
    archivo = models.FileField(upload_to=ruta_documento, blank=True, validators=VALIDADORES_PDF)
    enlace_drive = models.URLField("enlace a Drive", max_length=500, blank=True)
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
        
        if not self.archivo and not self.enlace_drive:
            raise ValidationError("Sube el archivo PDF o pega el enlace a Drive.")
        
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
    
class EnvioProveedor(models.Model):
    """Un documento que llegó de un proveedor y espera revisión: la "bandeja de envíos"."""
    ORIGENES = [
        ("portal", "Portal de proveedores"),
        ("manual", "Registro manual"),
    ]
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("procesado", "Procesado"),
        ("descartado", "Descartado"),
    ]
    origen = models.CharField(max_length=10, choices=ORIGENES, default="manual")
    id_externo = models.CharField(
        "id en el portal", max_length=50, unique=True, null=True, blank=True,
        help_text="Número del envío en el portal. Evita traer dos veces el mismo envío.",
    )
    nit = models.CharField("NIT enviado", max_length=20)
    razon_social = models.CharField("razón social enviada", max_length=200)
    tipo = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT, related_name="envios")
    archivo = models.FileField(upload_to=ruta_envio, validators=VALIDADORES_PDF)
    nombre_original = models.CharField("nombre original del archivo", max_length=255, blank=True)
    recibido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="pendiente")
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="envios",
    )
    documento = models.OneToOneField(
        DocumentoProveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="envio",
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    fecha_revision = models.DateTimeField("fecha de revisión", null=True, blank=True)
    motivo_descarte = models.CharField("motivo del descarte", max_length=300, blank=True)

    class Meta:
        ordering = ["-recibido"]
        verbose_name = "envío de proveedor"
        verbose_name_plural = "envíos de proveedores"

    def __str__(self):
        return f"{self.tipo} · {self.razon_social} ({self.get_estado_display()})"

    def clean(self):
        if self.estado == "descartado" and not self.motivo_descarte.strip():
            raise ValidationError({"motivo_descarte": "Escribe por qué se descarta el envío."})

    def save(self, *args, **kwargs):
        # Antes de guardar, el archivo todavía tiene el nombre con que lo subieron: lo anotamos.
        if self.archivo and not self.nombre_original:
            self.nombre_original = Path(self.archivo.name).name
        super().save(*args, **kwargs)

    def proveedor_sugerido(self):
        """El proveedor que ya tiene ese NIT (con o sin dígito de verificación), si existe."""
        return Proveedor.con_mismo_nit(self.nit).first()