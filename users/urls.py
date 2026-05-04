from django.urls import path
from .views import SignUpView
from . import views

urlpatterns = [
    path('registro/', SignUpView.as_view(), name='signup'),
    # Ruta para ver el perfil
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/<str:username>/', views.perfil_usuario, name='perfil_usuario'),
    # Ruta maestra para enviar, aceptar, rechazar o eliminar amigos
    path('amistad/<str:username>/<str:accion>/', views.accion_amistad, name='accion_amistad'),
    path('buscar/', views.buscar_usuarios, name='buscar_usuarios'),
    path('solicitudes/', views.solicitudes_view, name='solicitudes'),
    path('sugerencias/', views.sugerencias_view, name='sugerencias'),
    path('verificacion/', views.solicitar_verificacion, name='solicitar_verificacion'),
    path('mensajes/', views.chat_view, name='chat_general'),
    path('mensajes/<str:username>/', views.chat_view, name='chat_con_amigo'),
    path('api/enviar-mensaje/', views.enviar_mensaje_ajax, name='enviar_mensaje_ajax'),
    path('api/nuevos-mensajes/<str:username>/', views.obtener_mensajes_ajax, name='obtener_mensajes_ajax'),
    path('api/notificaciones-mensajes/', views.notificaciones_mensajes_ajax, name='notificaciones_mensajes_ajax'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('verificar-codigo/', views.verificar_otp, name='verificar_otp'),
    path('ajustes/', views.ajustes_view, name='ajustes'),
    path('ajustes/toggle/<str:campo>/', views.cambiar_booleano_ajustes, name='toggle_ajustes'),
    path('ajustes/email/', views.solicitar_cambio_email, name='cambiar_email'),
    path('ajustes/validar-otp/', views.validar_otp_ajustes, name='validar_otp_ajustes'),
    path('ajustes/eliminar/', views.eliminar_cuenta, name='eliminar_cuenta'),
    path('ajustes/password/', views.solicitar_cambio_password, name='cambiar_password'),
]