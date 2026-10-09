from django.urls import path

from . import views

app_name = 'configuracion'

urlpatterns = [
    path('', views.panel, name='panel'),
    path('areas/', views.areas_lista, name='areas'),
    path('areas/nueva/', views.area_guardar, name='area_nueva'),
    path('areas/<int:pk>/editar/', views.area_guardar, name='area_editar'),
    path('areas/<int:pk>/alternar/', views.area_alternar, name='area_alternar'),
    path('unidades/', views.unidades_lista, name='unidades'),
    path('unidades/nueva/', views.unidad_guardar, name='unidad_nueva'),
    path('unidades/<int:pk>/editar/', views.unidad_guardar, name='unidad_editar'),
    path('productos/', views.productos_lista, name='productos'),
    path('productos/nuevo/', views.producto_guardar, name='producto_nuevo'),
    path('productos/<int:pk>/editar/', views.producto_guardar, name='producto_editar'),
    path('productos/<int:pk>/alternar/', views.producto_alternar, name='producto_alternar'),
]