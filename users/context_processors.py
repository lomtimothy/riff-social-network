from .models import User, FriendRequest, MusicianVerificationRequest, Message

def social_data(request):
    if request.user.is_authenticated:
        # 1. Obtenemos las solicitudes de amistad recibidas
        solicitudes = FriendRequest.objects.filter(receiver=request.user)
        
        # 2. Obtenemos sugerencias (excluimos a ti mismo, a tus amigos y a los que ya tienen solicitud)
        amigos = request.user.friends.all()
        enviadas = FriendRequest.objects.filter(sender=request.user).values_list('receiver_id', flat=True)
        recibidas = FriendRequest.objects.filter(receiver=request.user).values_list('sender_id', flat=True)
        
        sugerencias = User.objects.exclude(id=request.user.id)\
                                  .exclude(id__in=amigos)\
                                  .exclude(id__in=enviadas)\
                                  .exclude(id__in=recibidas)[:5] # Máximo 5 sugerencias
        mensajes_sin_leer = Message.objects.filter(receiver=request.user, is_read=False).count()
        return {
            'solicitudes_pendientes': solicitudes,
            'sugerencias_amistad': sugerencias,
            'mensajes_sin_leer': mensajes_sin_leer
        }
    return {}