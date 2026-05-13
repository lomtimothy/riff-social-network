from .models import User, FriendRequest, Message

def social_data(request):
    if request.user.is_authenticated:
        # 1. Solicitudes recibidas
        solicitudes = FriendRequest.objects.filter(receiver=request.user)
        
        # Conteo de solicitudes NUEVAS (posteriores a la última visita)
        if request.user.last_viewed_requests:
            nuevas_solicitudes_count = solicitudes.filter(timestamp__gt=request.user.last_viewed_requests).count()
        else:
            nuevas_solicitudes_count = solicitudes.count()

        # 2. Sugerencias de amistad
        amigos = request.user.friends.all()
        enviadas = FriendRequest.objects.filter(sender=request.user).values_list('receiver_id', flat=True)
        recibidas = FriendRequest.objects.filter(receiver=request.user).values_list('sender_id', flat=True)
        
        sugerencias_qs = User.objects.exclude(id=request.user.id)\
                                     .exclude(id__in=amigos)\
                                     .exclude(id__in=enviadas)\
                                     .exclude(id__in=recibidas)
        
        # Conteo de sugerencias NUEVAS (basado en la fecha de registro del usuario sugerido)
        if request.user.last_viewed_suggestions:
            nuevas_sugerencias_count = sugerencias_qs.filter(date_joined__gt=request.user.last_viewed_suggestions).count()
        else:
            nuevas_sugerencias_count = sugerencias_qs.count()

        mensajes_sin_leer = Message.objects.filter(receiver=request.user, is_read=False).count()
        
        return {
            'solicitudes_pendientes': solicitudes,
            'nuevas_solicitudes_count': nuevas_solicitudes_count, # Enviamos el conteo de novedades
            'sugerencias_amistad': sugerencias_qs[:5],
            'nuevas_sugerencias_count': nuevas_sugerencias_count, # Enviamos el conteo de novedades
            'mensajes_sin_leer': mensajes_sin_leer,
            'amigos_activos': amigos
        }
    return {}

    def notification_data(request):
    if request.user.is_authenticated:
        return {'unread_notifications_count': request.user.notifications.filter(is_read=False).count()}
    return {}