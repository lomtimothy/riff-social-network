from django.urls import path
from . import views # Aquí sí importamos las vistas de esta carpeta

urlpatterns = [
    path('', views.feed_principal, name='feed'),
    path('nueva-resena/', views.crear_resena, name='crear_resena'),
    path('reaccionar/<int:resena_id>/<str:tipo>/', views.reaccionar, name='reaccionar'),
    path('comentar/<int:resena_id>/', views.comentar, name='comentar'), # Ya existía, asegúrate de tenerla
    path('comentario/<int:comentario_id>/eliminar/', views.eliminar_comentario, name='eliminar_comentario'),
    path('comentario/<int:comentario_id>/editar/', views.editar_comentario, name='editar_comentario'),
    path('comentario/<int:comentario_id>/reaccionar/<str:tipo>/', views.reaccionar_comentario, name='reaccionar_comentario'),
    path('resena/<int:resena_id>/eliminar/', views.eliminar_resena, name='eliminar_resena'),
    path('resena/<int:resena_id>/editar/', views.editar_resena, name='editar_resena'),
    path('concierto/nuevo/', views.agregar_concierto, name='agregar_concierto'),
]