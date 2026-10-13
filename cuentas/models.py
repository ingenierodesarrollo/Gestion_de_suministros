from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models


class Rol(models.TextChoices):
    COORDINADOR = 'coordinador', 'Coordinador de área'
    ADMINISTRADOR = 'administrador', 'Administrador'
    DESARROLLADOR = 'desarrollador', 'Desarrollador'


class UsuarioManager(BaseUserManager):
    """Crea usuarios usando el correo como identificador para iniciar sesión."""

    use_in_migrations = True

    def create_user(self, correo, nombre, password=None, **extra):
        if not correo:
            raise ValueError('El usuario debe tener un correo.')
        usuario = self.model(correo=self.normalize_email(correo), nombre=nombre, **extra)
        usuario.set_password(password)  # guarda la contraseña cifrada, nunca en texto plano
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, nombre, password=None, **extra):
        extra.setdefault('rol', Rol.DESARROLLADOR)
        extra['is_superuser'] = True
        return self.create_user(correo, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Persona que usa el sistema. Inicia sesión con su correo y contraseña."""

    nombre = models.CharField('nombre', max_length=150)
    correo = models.EmailField('correo', unique=True)
    rol = models.CharField('rol', max_length=20, choices=Rol.choices)
    area = models.ForeignKey(
        'areas.Area',
        verbose_name='área',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='usuarios',
    )
    activo = models.BooleanField('activo', default=True)
    # La contraseña cifrada vive en el campo "password" heredado de AbstractBaseUser.
    
    debe_cambiar_clave = models.BooleanField('debe cambiar la clave', default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo'
    EMAIL_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} <{self.correo}>'

    def clean(self):
        super().clean()
        if self.rol == Rol.COORDINADOR and not self.area_id:
            raise ValidationError({'area': 'Un coordinador de área debe tener un área asignada.'})

    # Django pregunta por "is_active" para permitir o no el inicio de sesión.
    @property
    def is_active(self):
        return self.activo

    # Solo un superusuario técnico entra al panel /admin/ de Django.
    @property
    def is_staff(self):
        return self.is_superuser

    @property
    def es_coordinador(self):
        return self.rol == Rol.COORDINADOR

    @property
    def es_administrador(self):
        return self.rol == Rol.ADMINISTRADOR

    @property
    def es_desarrollador(self):
        return self.rol == Rol.DESARROLLADOR
