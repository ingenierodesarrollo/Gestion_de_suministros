from django.shortcuts import redirect
from django.urls import reverse


class ForzarCambioClaveMiddleware:
    """Mientras el usuario tenga la marca, solo puede cambiar su clave o salir."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if usuario.is_authenticated and usuario.debe_cambiar_clave:
            permitidas = (reverse('cambiar_clave'), reverse('logout'))
            if request.path not in permitidas and not request.path.startswith('/static/'):
                return redirect('cambiar_clave')
        return self.get_response(request)