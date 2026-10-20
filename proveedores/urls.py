from django.urls import path

from . import views

app_name = "proveedores"

urlpatterns = [
    path("", views.proveedores_lista, name="lista"),
    path("nuevo/", views.proveedor_guardar, name="nuevo"),
    path("<int:pk>/", views.proveedor_detalle, name="detalle"),
    path("<int:pk>/editar/", views.proveedor_guardar, name="editar"),
]
