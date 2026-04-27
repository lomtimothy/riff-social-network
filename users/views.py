from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Max
from itertools import chain
from operator import attrgetter
from .forms import CustomUserCreationForm
from .models import User, FriendRequest
from music.models import Review, ConcertLog, IdealConcert, Playlist, Announcement, UpcomingConcert # <-- Importamos ambos modelos de music
from .models import User, FriendRequest, MusicianVerificationRequest, Message
from .forms import CustomUserCreationForm, MusicianVerificationForm
from django.db.models import Q, Count
from django.utils.timezone import localtime
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from .models import UserOTP # Asegúrate de agregarlo a tus importaciones de modelos
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save() # Se crea el usuario
        
        # Forzamos 2FA para validar el correo nuevo
        otp_profile, created = UserOTP.objects.get_or_create(user=user)
        codigo = otp_profile.generate_code()
        
        send_mail(
            '¡Bienvenido a Riff! Confirma tu cuenta 🎸',
            f'Hola {user.username}, tu código de activación es: {codigo}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        
        self.request.session['pre_otp_user_id'] = user.id
        return redirect('verificar_otp')


@login_required
def perfil_usuario(request, username):
    perfil = get_object_or_404(User, username=username)
    
    es_mi_perfil = (request.user == perfil)
    somos_amigos = perfil in request.user.friends.all()
    
    es_publico = not perfil.is_private
    puedo_ver = es_mi_perfil or somos_amigos or es_publico
    
    # --- LA NUEVA LÓGICA DE PUBLICACIONES ---
    publicaciones = []
    mis_albumes = [] # <--- NUEVO: Inicializamos la lista de álbumes oficial
    
    if puedo_ver:
        # 1. Obtenemos las reseñas de este usuario
        resenas = list(Review.objects.filter(user=perfil))
        for r in resenas: r.tipo_pub = 'resena'
            
        # 2. Obtenemos los conciertos de este usuario
        conciertos = list(ConcertLog.objects.filter(user=perfil))
        for c in conciertos: c.tipo_pub = 'concierto'
        
        # 3. Obtenemos los conciertos ideales de este usuario
        ideales = list(IdealConcert.objects.filter(user=perfil))
        for i in ideales: i.tipo_pub = 'ideal'

        # Playlists
        playlists = list(Playlist.objects.filter(user=perfil))
        for p in playlists: p.tipo_pub = 'playlist'

        # Anuncios (Tablón)
        anuncios = list(Announcement.objects.filter(user=perfil))
        for a in anuncios: a.tipo_pub = 'anuncio'

        # Agenda (Próximos conciertos)
        agenda = list(UpcomingConcert.objects.filter(user=perfil))
        for ag in agenda: ag.tipo_pub = 'proximo_concierto'
        
        # --- PASO 1 (NUEVO): TRAER LOS ÁLBUMES DEL CATÁLOGO OFICIAL (MIS COSAS) ---
        # Verificamos si el perfil tiene un perfil de artista asociado antes de pedir los álbumes
        if hasattr(perfil, 'artist_profile'):
            mis_albumes = perfil.artist_profile.albums.all().order_by('-created_at')
            
        # 4. Unimos TODO y ordenamos de más reciente a más antiguo
        publicaciones = sorted(chain(resenas, conciertos, ideales, playlists, anuncios, agenda), key=attrgetter('created_at'), reverse=True)      
        
    solicitud_enviada = FriendRequest.objects.filter(sender=request.user, receiver=perfil).exists()
    solicitud_recibida = FriendRequest.objects.filter(sender=perfil, receiver=request.user).exists()
    
    # --- CALCULAMOS LA LISTA DE TUS AMIGOS ACTIVOS ---
    mis_amigos = request.user.friends.all()
    amigos_activos = mis_amigos.annotate(
        ultima_actividad=Max('reviews__created_at')
    ).order_by('-ultima_actividad')
    
    context = {
        'perfil': perfil,
        'puedo_ver': puedo_ver,
        'publicaciones': publicaciones, 
        'mis_albumes': mis_albumes, # <--- NUEVO: Pasamos los álbumes al contexto del HTML
        'es_mi_perfil': es_mi_perfil,
        'somos_amigos': somos_amigos,
        'solicitud_enviada': solicitud_enviada,
        'solicitud_recibida': solicitud_recibida,
        'amigos_activos': amigos_activos, 
    }
    return render(request, 'users/perfil.html', context)

@login_required
def accion_amistad(request, username, accion):
    target_user = get_object_or_404(User, username=username)
    
    # ADAPTADO A TU MODELO: Usamos 'sender' y 'receiver'
    if accion == 'enviar' and target_user != request.user:
        FriendRequest.objects.get_or_create(sender=request.user, receiver=target_user)
        
    elif accion == 'aceptar':
        solicitud = FriendRequest.objects.filter(sender=target_user, receiver=request.user).first()
        if solicitud:
            request.user.friends.add(target_user)
            # Como pusiste symmetrical=True en tu modelo, agregarlo de un lado lo agrega del otro automáticamente
            solicitud.delete() # Borramos la solicitud para limpiar la base de datos
            
    elif accion == 'rechazar' or accion == 'cancelar':
        FriendRequest.objects.filter(sender=target_user, receiver=request.user).delete()
        FriendRequest.objects.filter(sender=request.user, receiver=target_user).delete()
        
    elif accion == 'eliminar':
        request.user.friends.remove(target_user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
        
    return redirect('perfil_usuario', username=username)

@login_required
def buscar_usuarios(request):
    # Obtenemos lo que el usuario escribió en la barra de búsqueda (el parámetro 'q')
    query = request.GET.get('q', '')
    usuarios_encontrados = []

    if query:
        # Buscamos usuarios cuyo username contenga el texto buscado (ignorando mayúsculas/minúsculas)
        # Excluimos al propio usuario que está haciendo la búsqueda
        usuarios_encontrados = User.objects.filter(username__icontains=query).exclude(id=request.user.id)

    context = {
        'query': query,
        'usuarios_encontrados': usuarios_encontrados
    }
    return render(request, 'users/buscar.html', context)

@login_required
def solicitudes_view(request):
    # El Context Processor ya nos envía 'solicitudes_pendientes', 
    # así que solo necesitamos renderizar la plantilla.
    return render(request, 'users/solicitudes.html')

@login_required
def sugerencias_view(request):
    # La lista de 'sugerencias_amistad' ya viaja automáticamente por el Context Processor
    return render(request, 'users/sugerencias.html')

@login_required
def solicitar_verificacion(request):
    # Si ya es músico verificado, lo mandamos a su perfil (no tiene nada que hacer aquí)
    if request.user.is_musician:
        return redirect('perfil_usuario', username=request.user.username)
    
    # Buscamos si ya tiene una solicitud creada
    solicitud_existente = MusicianVerificationRequest.objects.filter(user=request.user).first()

    if request.method == 'POST':
        form = MusicianVerificationForm(request.POST, instance=solicitud_existente)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.user = request.user
            # ¡CLAVE! Siempre que el usuario guarde el formulario, lo pasamos a PENDIENTE
            # Así, si estaba rechazado y lo intentó de nuevo, tú podrás volver a evaluarlo.
            solicitud.status = 'PENDING' 
            solicitud.save()
            
            # En vez de mandarlo al perfil, recargamos esta misma página para que vea el mensaje amarillo
            return redirect('solicitar_verificacion') 
    else:
        form = MusicianVerificationForm(instance=solicitud_existente)

    return render(request, 'users/solicitar_verificacion.html', {'form': form, 'solicitud': solicitud_existente})

@login_required
def chat_view(request, username=None):
    amigos = request.user.friends.annotate(
        unread_count=Count('sent_messages', filter=Q(sent_messages__receiver=request.user, sent_messages__is_read=False))
    )
    amigo_actual = None
    mensajes = []

    if username:
        amigo_actual = get_object_or_404(User, username=username)
        
        # --- SOLUCIÓN AQUÍ ---
        # Seguridad: Verificamos la amistad consultando directo a la base de datos pura, 
        # para evitar el conflicto con la lista 'amigos' que ahora trae el contador anotado.
        if not request.user.friends.filter(username=username).exists():
            return redirect('chat_general')
            
        # Cargar el historial de conversación entre ambos
        mensajes = Message.objects.filter(
            Q(sender=request.user, receiver=amigo_actual) | 
            Q(sender=amigo_actual, receiver=request.user)
        ).order_by('created_at')
        
        # Marcar los mensajes que me envió como leídos
        Message.objects.filter(sender=amigo_actual, receiver=request.user, is_read=False).update(is_read=True)

    return render(request, 'users/chat.html', {
        'amigos': amigos,
        'amigo': amigo_actual,
        'mensajes': mensajes
    })

# 2. API PARA ENVIAR (AJAX)
@login_required
def enviar_mensaje_ajax(request):
    if request.method == 'POST':
        receiver_username = request.POST.get('receiver')
        text = request.POST.get('text')
        if text and receiver_username:
            receiver = User.objects.get(username=receiver_username)
            msg = Message.objects.create(sender=request.user, receiver=receiver, text=text)
            return JsonResponse({'success': True, 'text': msg.text, 'created_at': localtime(msg.created_at).strftime("%H:%M")})
    return JsonResponse({'success': False})

# 3. API PARA RECIBIR (POLLING)
@login_required
def obtener_mensajes_ajax(request, username):
    amigo = get_object_or_404(User, username=username)
    # Buscamos solo los mensajes nuevos que me haya mandado ese amigo
    nuevos = Message.objects.filter(sender=amigo, receiver=request.user, is_read=False)
    
    data = []
    for msg in nuevos:
        data.append({'text': msg.text, 'created_at': localtime(msg.created_at).strftime("%H:%M")})
        msg.is_read = True # Los marcamos como leídos
        msg.save()
        
    return JsonResponse({'mensajes': data})

@login_required
def notificaciones_mensajes_ajax(request):
    # Traemos todos los mensajes sin leer
    mensajes_sin_leer = Message.objects.filter(receiver=request.user, is_read=False)
    total = mensajes_sin_leer.count()
    
    # Agrupamos cuántos mensajes mandó cada usuario
    agrupados = mensajes_sin_leer.values('sender__username').annotate(count=Count('id'))
    
    # Creamos un diccionario limpio { 'LauraMendez': 2, 'RicardoTorres': 1 }
    conteo_por_contacto = {item['sender__username']: item['count'] for item in agrupados}
    
    return JsonResponse({
        'total': total,
        'by_sender': conteo_por_contacto
    })

# INTERCEPTAMOS EL LOGIN NORMAL
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    
    def form_valid(self, form):
        # El usuario puso bien su usuario y contraseña
        user = form.get_user()
        
        # --- LÓGICA OPCIONAL DE 2FA ---
        if user.two_factor_login:
            # 1. Si tiene el 2FA activado, generamos código y mandamos correo
            otp_profile, created = UserOTP.objects.get_or_create(user=user)
            codigo = otp_profile.generate_code()
            
            send_mail(
                'Tu código de seguridad Riff 🎸',
                f'Hola {user.username}, ingresa este código para acceder: {codigo}',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
            
            # 2. Lo mandamos a la sala de espera
            self.request.session['pre_otp_user_id'] = user.id
            return redirect('verificar_otp')
        else:
            # 3. Si lo tiene desactivado, iniciamos sesión normalmente al instante
            auth_login(self.request, user)
            return redirect('feed')

# LA SALA DE ESPERA (2FA)
def verificar_otp(request):
    # Revisamos si hay alguien en la "sala de espera"
    user_id = request.session.get('pre_otp_user_id')
    if not user_id:
        return redirect('login') # Si intentan entrar directo a la URL, los regresamos
        
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo')
        user = User.objects.get(id=user_id)
        
        # Comparamos el código
        if hasattr(user, 'otp') and user.otp.code == codigo_ingresado:
            # ¡ES CORRECTO! 
            user.otp.code = None # Borramos el código por seguridad para que no se re-use
            user.otp.save()
            
            del request.session['pre_otp_user_id'] # Lo sacamos de la sala de espera
            
            auth_login(request, user) # ¡POR FIN LE ABRIMOS LA PUERTA REAL!
            return redirect('feed')
        else:
            return render(request, 'users/verificar_otp.html', {'error': 'Código incorrecto. Revisa tu correo e intenta de nuevo unu.'})
            
    return render(request, 'users/verificar_otp.html')

@login_required
def ajustes_view(request):
    return render(request, 'users/ajustes.html')

# 2. TOGGLE PARA PRIVACIDAD Y 2FA
@login_required
def cambiar_booleano_ajustes(request, campo):
    if campo == 'privacidad' and not request.user.is_musician:
        request.user.is_private = not request.user.is_private
    elif campo == '2fa':
        request.user.two_factor_login = not request.user.two_factor_login
    
    request.user.save()
    return redirect('ajustes')

# 3. CAMBIAR CORREO (CON OTP)
@login_required
def solicitar_cambio_email(request):
    if request.method == 'POST':
        nuevo_email = request.POST.get('email')
        password = request.POST.get('password')
        
        if request.user.check_password(password):
            # Guardamos el email temporalmente en la sesión
            request.session['pending_new_email'] = nuevo_email
            
            # Reutilizamos tu lógica de OTP
            otp_profile, _ = UserOTP.objects.get_or_create(user=request.user)
            codigo = otp_profile.generate_code()
            
            send_mail(
                'Confirma tu nuevo correo en Riff 🎸',
                f'Tu código para cambiar de correo es: {codigo}',
                settings.EMAIL_HOST_USER,
                [nuevo_email],
            )
            return render(request, 'users/confirmar_ajuste_otp.html', {'tipo': 'email'})
        else:
            messages.error(request, "Contraseña incorrecta.")
    return redirect('ajustes')

# 4. ELIMINAR CUENTA definitivamente
@login_required
def eliminar_cuenta(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        if request.user.check_password(password):
            user = request.user
            user.delete()
            messages.success(request, "Tu cuenta ha sido eliminada. Lamentamos verte partir unu.")
            return redirect('login')
        else:
            messages.error(request, "Contraseña incorrecta.")
    return redirect('ajustes')

# VISTA PARA VALIDAR EL OTP DE AJUSTES
@login_required
def validar_otp_ajustes(request):
    codigo = request.POST.get('codigo')
    if hasattr(request.user, 'otp') and request.user.otp.code == codigo:
        
        # ¿Viene de cambiar EMAIL?
        if 'pending_new_email' in request.session:
            request.user.email = request.session['pending_new_email']
            request.user.save()
            del request.session['pending_new_email']
            messages.success(request, "Correo actualizado con máxima seguridad.")
            
        # ¿Viene de cambiar PASSWORD?
        if 'pending_new_password' in request.session:
            # Seteamos la contraseña encriptada
            request.user.set_password(request.session['pending_new_password'])
            request.user.save()
            
            # MAGIA: Le decimos a Django que no le cierre la sesión al usuario
            update_session_auth_hash(request, request.user) 
            
            del request.session['pending_new_password']
            messages.success(request, "¡Tu contraseña fue actualizada exitosamente!")

        # Destruimos el código por seguridad
        request.user.otp.code = None
        request.user.otp.save()
        return redirect('ajustes')
    else:
        return render(request, 'users/confirmar_ajuste_otp.html', {'error': 'El código es inválido o ha expirado unu.'})

@login_required
def solicitar_cambio_password(request):
    if request.method == 'POST':
        password_actual = request.POST.get('password_actual')
        nueva_password = request.POST.get('nueva_password')
        confirmar_password = request.POST.get('confirmar_password')
        
        # Validamos que las contraseñas coincidan y la actual sea correcta
        if nueva_password != confirmar_password:
            messages.error(request, "Las contraseñas nuevas no coinciden.")
            return redirect('ajustes')
            
        if request.user.check_password(password_actual):
            # Guardamos la nueva contraseña en la sesión temporalmente
            request.session['pending_new_password'] = nueva_password
            
            otp_profile, _ = UserOTP.objects.get_or_create(user=request.user)
            codigo = otp_profile.generate_code()
            
            send_mail(
                'Alerta de Seguridad: Cambio de Contraseña 🎸',
                f'Hola {request.user.username}, ingresa este código para confirmar tu cambio de contraseña: {codigo}\n\nSi no fuiste tú, alguien tiene tu contraseña actual. Cambia tus credenciales de inmediato.',
                settings.EMAIL_HOST_USER,
                [request.user.email],
            )
            return render(request, 'users/confirmar_ajuste_otp.html')
        else:
            messages.error(request, "Tu contraseña actual es incorrecta.")
    return redirect('ajustes')