from django.urls import path

from . import views

app_name = 'proyecciones'

urlpatterns = [
    path('mi-proyeccion/', views.mi_proyeccion, name='mi_proyeccion'),
    path('<int:pk>/', views.detalle_proyeccion, name='detalle'),
    path('<int:pk>/agregar-linea/', views.agregar_linea, name='agregar_linea'),
    path('linea/<int:pk>/editar/', views.editar_linea, name='editar_linea'),
    path('linea/<int:pk>/borrar/', views.borrar_linea, name='borrar_linea'),
    path('<int:pk>/enviar/', views.enviar_proyeccion, name = 'enviar'),
    path('revision/',views.revision, name = 'revision'),
    path('<int:pk>/revisar/', views.revisar_proyeccion, name='revisar'),
]