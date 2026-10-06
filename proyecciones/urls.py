from django.urls import path

from . import views

app_name = 'proyecciones'

urlpatterns = [
    path('mi-proyeccion/', views.mi_proyeccion, name='mi_proyeccion'),
    path('<int:pk>/', views.detalle_proyeccion, name='detalle'),
]