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
from .models import User, FriendRequest, MusicianVerificationRequest
from .forms import CustomUserCreationForm, MusicianVerificationForm

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    # Si el registro es exitoso, lo mandamos a iniciar sesión
    success_url = reverse_lazy('login') 
    template_name = 'registration/signup.html'


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