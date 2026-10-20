from django.urls import path

from . import bandeja, views

app_name = "proveedores"

urlpatterns = [
    path("", views.proveedores_lista, name="lista"),
    path("bandeja/", bandeja.bandeja_lista, name="bandeja"),
    path("bandeja/<int:pk>/", bandeja.bandeja_detalle, name="bandeja_detalle"),
    path("bandeja/<int:pk>/procesar/", bandeja.envio_procesar, name="envio_procesar"),
    path("bandeja/<int:pk>/descartar/", bandeja.envio_descartar, name="envio_descartar"),
    path("bandeja/<int:pk>/archivo/", bandeja.envio_archivo, name="envio_archivo"),
    path("documentos/<int:pk>/archivo/", bandeja.documento_archivo, name="documento_archivo"),
    path("nuevo/", views.proveedor_guardar, name="nuevo"),
    path("<int:pk>/", views.proveedor_detalle, name="detalle"),
    path("<int:pk>/editar/", views.proveedor_guardar, name="editar"),
]
