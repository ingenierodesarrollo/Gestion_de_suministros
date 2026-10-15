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
    path('<int:pk>/aprobar/', views.aprobar_proyeccion, name = 'aprobar'),
    path('abrir-periodo/', views.abrir_periodo_vista, name='abrir_periodo'),
    path('linea/<int:pk>/corregir/', views.corregir_linea, name='corregir_linea'),
    path('periodo/<int:pk>/alternar/', views.alternar_periodo_vista, name='alternar_periodo'),
    path('bitacora/', views.bitacora, name='bitacora'),
    path('consolidado/', views.consolidado_vista, name='consolidado'),
    path('consolidado/<int:anio>/excel/', views.descargar_consolidado, name='descargar_consolidado'),
    path('plantilla-excel/', views.descargar_plantilla, name='plantilla_excel'),
    path('<int:pk>/importar-excel/', views.importar_excel, name='importar_excel'),
    path('<int:pk>/importar-excel/confirmar/', views.confirmar_importacion, name='confirmar_importacion'),
]