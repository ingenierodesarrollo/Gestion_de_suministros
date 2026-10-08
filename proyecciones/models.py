from django.conf import settings
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator


class EstadoPeriodo(models.TextChoices):
    ABIERTO = 'abierto', 'Abierto'
    CERRADO = 'cerrado', 'Cerrado'


class Periodo(models.Model):
    """Año de la proyección de compras, con sus fechas de apertura y límite."""

    anio = models.PositiveSmallIntegerField('año', unique=True)
    fecha_apertura = models.DateField('fecha de apertura')
    fecha_limite = models.DateField('fecha límite de envío')
    estado = models.CharField(
        'estado', max_length=10, choices=EstadoPeriodo.choices, default=EstadoPeriodo.ABIERTO
    )
    abierto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='abierto por',
        on_delete=models.PROTECT,
        related_name='periodos_abiertos',
    )

    class Meta:
        verbose_name = 'periodo'
        verbose_name_plural = 'periodos'
        ordering = ['-anio']

    def __str__(self):
        return str(self.anio)


class UnidadMedida(models.Model):
    """Unidad en que se pide un producto: Unidad, Caja x 100, Litro..."""

    nombre = models.CharField('nombre', max_length=40, unique=True)

    class Meta:
        verbose_name = 'unidad de medida'
        verbose_name_plural = 'unidades de medida'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
    
class EstadoProyeccion(models.TextChoices):
    BORRADOR = 'borrador', 'Borrador'
    ENVIADA = 'enviada', 'Enviada'
    APROBADA = 'aprobada', 'Aprobada'


class ProyeccionArea(models.Model):
    """Proyección anual de compras de un área."""

    periodo = models.ForeignKey(
        Periodo, verbose_name='periodo', on_delete=models.PROTECT, related_name='proyecciones'
    )
    area = models.ForeignKey(
        'areas.Area', verbose_name='área', on_delete=models.PROTECT, related_name='proyecciones'
    )
    estado = models.CharField(
        'estado', max_length=10, choices=EstadoProyeccion.choices, default=EstadoProyeccion.BORRADOR
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='responsable',
        on_delete=models.PROTECT,
        related_name='proyecciones_a_cargo',
    )
    fecha_envio = models.DateTimeField('fecha de envío', null=True, blank=True)
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='aprobada por',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='proyecciones_aprobadas',
    )
    fecha_aprobacion = models.DateTimeField('fecha de aprobación', null=True, blank=True)
    observaciones = models.TextField('observaciones', blank=True)

    class Meta:
        verbose_name = 'proyección de área'
        verbose_name_plural = 'proyecciones de área'
        ordering = ['-periodo__anio', 'area__nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['periodo', 'area'], name='una_proyeccion_por_periodo_y_area'
            )
        ]

    def __str__(self):
        return f'{self.area} · {self.periodo}'
    
class Linea(models.Model):
    """Un producto, equipo o servicio dentro de la proyección de un área."""

    proyeccion = models.ForeignKey(
        ProyeccionArea, verbose_name='proyección', on_delete=models.CASCADE, related_name='lineas'
    )
    producto = models.CharField('equipo / producto / servicio', max_length=150)
    dependencia = models.CharField('dependencia', max_length=100, blank=True)
    serie = models.CharField('serie', max_length=100, blank=True)
    unidad = models.ForeignKey(UnidadMedida, verbose_name='unidad', on_delete=models.PROTECT)

    ene = models.PositiveIntegerField('enero', default=0)
    feb = models.PositiveIntegerField('febrero', default=0)
    mar = models.PositiveIntegerField('marzo', default=0)
    abr = models.PositiveIntegerField('abril', default=0)
    may = models.PositiveIntegerField('mayo', default=0)
    jun = models.PositiveIntegerField('junio', default=0)
    jul = models.PositiveIntegerField('julio', default=0)
    ago = models.PositiveIntegerField('agosto', default=0)
    sep = models.PositiveIntegerField('septiembre', default=0)
    oct = models.PositiveIntegerField('octubre', default=0)
    nov = models.PositiveIntegerField('noviembre', default=0)
    dic = models.PositiveIntegerField('diciembre', default=0)

    precio_unitario_est = models.DecimalField(
        'precio unitario estimado',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    cantidad_autorizada = models.PositiveIntegerField(
        'cantidad autorizada (año)', null=True, blank=True
    )

    MESES = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')

    class Meta:
        verbose_name = 'línea de proyección'
        verbose_name_plural = 'líneas de proyección'
        ordering = ['id']

    def __str__(self):
        return self.producto

    @property
    def total_anual(self):
        return sum(getattr(self, mes) for mes in self.MESES)
    
    @property
    def costo(self):
        if self.precio_unitario_est is None:
            return 0
        return self.total_anual * self.precio_unitario_est
    
class ProductoSugerido(models.Model):
    """Nombre de producto que se ofrece como sugerencia al escribir una línea. La línea sigue siendo texto libre."""

    nombre = models.CharField('nombre', max_length=150, unique=True)
    activo = models.BooleanField('activo', default=True)

    class Meta:
        verbose_name = 'producto sugerido'
        verbose_name_plural = 'productos sugeridos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
    
    