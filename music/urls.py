from django.urls import path
from . import views

urlpatterns = [
    path('', views.feed_principal, name='feed'),
    path('nueva-resena/', views.crear_resena, name='crear_resena'),
    path('concierto/nuevo/', views.agregar_concierto, name='agregar_concierto'),

    # RUTAS UNIFICADAS PARA INTERACCIONES GLOBALES
    path('reaccionar/<str:tipo_pub>/<int:id>/<str:tipo>/', views.reaccionar, name='reaccionar'),
    path('comentar/<str:tipo_pub>/<int:id>/', views.comentar, name='comentar'),
    path('publicacion/<str:tipo_pub>/<int:id>/eliminar/', views.eliminar_publicacion, name='eliminar_publicacion'),
    path('publicacion/<str:tipo_pub>/<int:id>/editar/', views.editar_publicacion, name='editar_publicacion'),

    # Comentarios recursivos (no cambian porque apuntan a su propio ID de tabla)
    path('comentario/<int:comentario_id>/eliminar/', views.eliminar_comentario, name='eliminar_comentario'),
    path('comentario/<int:comentario_id>/editar/', views.editar_comentario, name='editar_comentario'),
    path('comentario/<int:comentario_id>/reaccionar/<str:tipo>/', views.reaccionar_comentario, name='reaccionar_comentario'),
    path('concierto-ideal/nuevo/', views.crear_concierto_ideal, name='crear_concierto_ideal'),
]