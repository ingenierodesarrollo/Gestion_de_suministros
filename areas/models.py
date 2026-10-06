from django.db import models


class Area(models.Model):
    """Un área de la clínica (por ejemplo: Urgencias, Laboratorio)."""

    nombre = models.CharField('nombre', max_length=150)
    codigo_area = models.CharField('código de área', max_length=20, unique=True)
    activa = models.BooleanField('activa', default=True)

    class Meta:
        verbose_name = 'área'
        verbose_name_plural = 'áreas'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo_area} - {self.nombre}'
