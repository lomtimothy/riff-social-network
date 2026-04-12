from django.urls import path
from .views import SignUpView
from . import views

urlpatterns = [
    path('registro/', SignUpView.as_view(), name='signup'),
    # Ruta para ver el perfil
    path('perfil/<str:username>/', views.perfil_usuario, name='perfil_usuario'),
    # Ruta maestra para enviar, aceptar, rechazar o eliminar amigos
    path('amistad/<str:username>/<str:accion>/', views.accion_amistad, name='accion_amistad'),
    path('buscar/', views.buscar_usuarios, name='buscar_usuarios'),
    path('solicitudes/', views.solicitudes_view, name='solicitudes'),
    path('sugerencias/', views.sugerencias_view, name='sugerencias'),
    path('verificacion/', views.solicitar_verificacion, name='solicitar_verificacion'),
]