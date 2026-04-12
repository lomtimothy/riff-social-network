from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Max
from itertools import chain
from operator import attrgetter
import requests
import json

# IMPORTACIONES DE MODELOS Y FORMULARIOS (Todos completos)
from .models import Review, Reaction, Comment, CommentReaction, ConcertLog, IdealConcert, Playlist
from .forms import ReviewForm, ConcertLogForm, IdealConcertForm, PlaylistForm


# --- FUNCIÓN AYUDANTE ---
def get_pub_obj_and_kwargs(tipo_pub, obj_id):
    """Identifica de qué tabla viene la publicación para no repetir código"""
    if tipo_pub == 'resena':
        obj = get_object_or_404(Review, id=obj_id)
        return obj, {'review': obj}
    elif tipo_pub == 'concierto':
        obj = get_object_or_404(ConcertLog, id=obj_id)
        return obj, {'concert': obj}
    elif tipo_pub == 'ideal':
        obj = get_object_or_404(IdealConcert, id=obj_id)
        return obj, {'ideal_concert': obj}
    elif tipo_pub == 'playlist':
        obj = get_object_or_404(Playlist, id=obj_id)
        return obj, {'playlist': obj}
    else:
        raise Http404("Tipo de publicación no válido")


# --- VISTA DEL FEED (Actualizada con Conciertos Ideales) ---
@login_required
def feed_principal(request):
    amigos = request.user.friends.all()
    
    resenas = list(Review.objects.filter(Q(user__in=amigos) | Q(user=request.user)))
    for r in resenas: r.tipo_pub = 'resena'
              
    conciertos = list(ConcertLog.objects.filter(Q(user__in=amigos) | Q(user=request.user)))
    for c in conciertos: c.tipo_pub = 'concierto'

    ideales = list(IdealConcert.objects.filter(Q(user__in=amigos) | Q(user=request.user)))
    for i in ideales: i.tipo_pub = 'ideal'
    
    playlists = list(Playlist.objects.filter(Q(user__in=amigos) | Q(user=request.user)))
    for p in playlists: p.tipo_pub = 'playlist'

    # Unimos las TRES listas
    publicaciones = sorted(chain(resenas, conciertos, ideales, playlists), key=attrgetter('created_at'), reverse=True)

    amigos_activos = amigos.annotate(
        ultima_actividad=Max('reviews__created_at')
    ).order_by('-ultima_actividad')
              
    return render(request, 'music/feed.html', {
        'publicaciones': publicaciones,
        'amigos_activos': amigos_activos 
    })


# --- CREACIÓN DE PUBLICACIONES ---
@login_required
def crear_resena(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            nueva_resena = form.save(commit=False)
            nueva_resena.user = request.user
            
            spotify_link = form.cleaned_data.get('spotify_url')
            if spotify_link:
                if '/track/' in spotify_link: tipo = 'Canción 🎵'
                elif '/album/' in spotify_link: tipo = 'Álbum 💿'
                elif '/artist/' in spotify_link: tipo = 'Artista 🎤'
                elif '/playlist/' in spotify_link: tipo = 'Playlist 🎧'
                else: tipo = 'Entidad Musical 🎶'
                
                # API OFICIAL DE SPOTIFY
                api_url = f"https://open.spotify.com/oembed?url={spotify_link}"
                try:
                    respuesta = requests.get(api_url).json()
                    nueva_resena.entity_name = respuesta.get('title', 'Título Desconocido')
                    nueva_resena.image_url = respuesta.get('thumbnail_url', '')
                    nueva_resena.entity_type = tipo
                    nueva_resena.spotify_url = spotify_link
                except:
                    nueva_resena.entity_name = "Enlace de Spotify"
                    nueva_resena.entity_type = tipo

            nueva_resena.save()
            return redirect('feed')
    else:
        form = ReviewForm()
    return render(request, 'music/crear_resena.html', {'form': form})

@login_required
def agregar_concierto(request):
    if request.method == 'POST':
        form = ConcertLogForm(request.POST, request.FILES)
        if form.is_valid():
            concierto = form.save(commit=False)
            concierto.user = request.user
            
            spotify_link = form.cleaned_data.get('enlace_spotify')
            # API OFICIAL DE SPOTIFY
            api_url = f"https://open.spotify.com/oembed?url={spotify_link}"
            
            try:
                respuesta = requests.get(api_url).json()
                concierto.artista = respuesta.get('title', 'Artista Desconocido')
                concierto.imagen_artista = respuesta.get('thumbnail_url', '') 
            except:
                concierto.artista = "Artista Desconocido"
                concierto.imagen_artista = ""
            
            concierto.save()
            return redirect('perfil_usuario', username=request.user.username)
    else:
        form = ConcertLogForm()
    return render(request, 'music/crear_concierto.html', {'form': form})

@login_required
def crear_concierto_ideal(request):
    if request.method == 'POST':
        form = IdealConcertForm(request.POST)
        if form.is_valid():
            ideal = form.save(commit=False)
            ideal.user = request.user
            
            spotify_link = form.cleaned_data.get('enlace_spotify')
            # API OFICIAL DE SPOTIFY
            api_url = f"https://open.spotify.com/oembed?url={spotify_link}"
            try:
                respuesta = requests.get(api_url).json()
                ideal.artista = respuesta.get('title', 'Artista Desconocido')
                ideal.imagen_artista = respuesta.get('thumbnail_url', '')
            except:
                ideal.artista = "Artista Desconocido"
            
            ideal.save()
            return redirect('feed')
    else:
        form = IdealConcertForm()
    return render(request, 'music/crear_concierto_ideal.html', {'form': form})

# --- INTERACCIONES GLOBALES (Likes, Comentarios, Editar, Eliminar) ---
@login_required
def reaccionar(request, tipo_pub, id, tipo):
    obj, kwargs = get_pub_obj_and_kwargs(tipo_pub, id)
    
    reaccion = Reaction.objects.filter(user=request.user, **kwargs).first()
    if reaccion:
        if reaccion.reaction_type == tipo: reaccion.delete()
        else:
            reaccion.reaction_type = tipo
            reaccion.save()
    else:
        Reaction.objects.create(user=request.user, reaction_type=tipo, **kwargs)
        
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'likes': obj.likes_count, 'dislikes': obj.dislikes_count})
    return redirect('feed')

@login_required
def comentar(request, tipo_pub, id):
    if request.method == 'POST':
        texto = request.POST.get('comentario')
        parent_id = request.POST.get('parent_id')
        obj, kwargs = get_pub_obj_and_kwargs(tipo_pub, id)
            
        if texto:
            parent_obj = get_object_or_404(Comment, id=parent_id) if parent_id else None
            nuevo_comentario = Comment.objects.create(user=request.user, text=texto, parent=parent_obj, **kwargs)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                html = render_to_string('music/comentario_recursivo.html', {'comentario': nuevo_comentario, 'objeto': obj, 'tipo_pub': tipo_pub}, request=request)
                return JsonResponse({'html': html, 'parent_id': parent_id, 'comments_count': obj.comments.count()})
    return redirect('feed')

@login_required
def editar_publicacion(request, tipo_pub, id):
    obj, _ = get_pub_obj_and_kwargs(tipo_pub, id)
    
    # Seguridad: Solo el dueño puede editar su publicación
    if request.user != obj.user:
        return redirect('feed')
        
    if request.method == 'POST':
        # 1. Cargamos el formulario con los datos modificados por el usuario
        if tipo_pub == 'resena':
            form = ReviewForm(request.POST, instance=obj)
        elif tipo_pub == 'concierto':
            form = ConcertLogForm(request.POST, request.FILES, instance=obj)
        elif tipo_pub == 'ideal':
            form = IdealConcertForm(request.POST, instance=obj)
        elif tipo_pub == 'playlist':
            form = PlaylistForm(request.POST, request.FILES, instance=obj)
            
        if form.is_valid():
            pub = form.save(commit=False)
            
            # 2. Re-verificamos con Spotify por si el usuario cambió el enlace
            spotify_link = form.cleaned_data.get('spotify_url') if tipo_pub == 'resena' else form.cleaned_data.get('enlace_spotify')
            if spotify_link:
                api_url = f"https://open.spotify.com/oembed?url={spotify_link}"
                try:
                    respuesta = requests.get(api_url).json()
                    if tipo_pub == 'resena':
                        pub.entity_name = respuesta.get('title', 'Título Desconocido')
                        pub.image_url = respuesta.get('thumbnail_url', '')
                        if '/track/' in spotify_link: pub.entity_type = 'Canción 🎵'
                        elif '/album/' in spotify_link: pub.entity_type = 'Álbum 💿'
                        elif '/artist/' in spotify_link: pub.entity_type = 'Artista 🎤'
                        elif '/playlist/' in spotify_link: pub.entity_type = 'Playlist 🎧'
                        else: pub.entity_type = 'Entidad Musical 🎶'
                    else:
                        pub.artista = respuesta.get('title', 'Artista Desconocido')
                        pub.imagen_artista = respuesta.get('thumbnail_url', '')
                except:
                    pass # Si falla, mantiene la información que ya tenía
                    
            pub.save()
            return redirect('perfil_usuario', username=request.user.username)
    else:
        # 3. MODO LECTURA (GET): Cargamos el formulario pre-llenado con "instance=obj"
        if tipo_pub == 'resena':
            form = ReviewForm(instance=obj)
            template = 'music/crear_resena.html'
        elif tipo_pub == 'concierto':
            form = ConcertLogForm(instance=obj)
            template = 'music/crear_concierto.html'
        elif tipo_pub == 'ideal':
            form = IdealConcertForm(instance=obj)
            template = 'music/crear_concierto_ideal.html'
        elif tipo_pub == 'playlist':
            form = PlaylistForm(instance=obj)
            template = 'music/crear_playlist.html'
            
        return render(request, template, {'form': form, 'edit_mode': True})

@login_required
def eliminar_publicacion(request, tipo_pub, id):
    obj, _ = get_pub_obj_and_kwargs(tipo_pub, id)
    if request.user == obj.user: obj.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return JsonResponse({'success': True})
    return redirect('feed')


# --- INTERACCIONES DE COMENTARIOS (Hijos) ---
@login_required
def eliminar_comentario(request, comentario_id):
    comentario = get_object_or_404(Comment, id=comentario_id)
    
    # Descubrimos a quién pertenece el comentario para devolver el conteo correcto
    if comentario.review: obj = comentario.review
    elif comentario.concert: obj = comentario.concert
    elif comentario.ideal_concert: obj = comentario.ideal_concert
    else: obj = comentario.playlist
    
    if request.user == comentario.user:
        comentario.delete()
        
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'comments_count': obj.comments.count()})
    return redirect('feed')

@login_required
def editar_comentario(request, comentario_id):
    comentario = get_object_or_404(Comment, id=comentario_id)
    if request.method == 'POST':
        nuevo_texto = request.POST.get('texto')
        if nuevo_texto and request.user == comentario.user:
            comentario.text = nuevo_texto
            comentario.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'text': nuevo_texto})
        return redirect('feed')
    return render(request, 'music/editar_comentario.html', {'comentario': comentario})

@login_required
def reaccionar_comentario(request, comentario_id, tipo):
    comentario = get_object_or_404(Comment, id=comentario_id)
    reaccion, created = CommentReaction.objects.get_or_create(
        comment=comentario, user=request.user, defaults={'reaction_type': tipo}
    )
    if not created:
        if reaccion.reaction_type == tipo: reaccion.delete()
        else:
            reaccion.reaction_type = tipo
            reaccion.save()
            
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'likes': comentario.likes_count, 'dislikes': comentario.dislikes_count})
    return redirect('feed')

@login_required
def validar_cancion_ideal(request):
    """Vista AJAX para verificar inteligentemente que una canción pertenece al artista"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            track_url = data.get('track_url', '')
            artist_url = data.get('artist_url', '')

            if not track_url or not artist_url:
                return JsonResponse({'valid': False, 'error': 'Faltan enlaces.'})
            if '/track/' not in track_url:
                return JsonResponse({'valid': False, 'error': 'El enlace debe ser de una CANCIÓN de Spotify.'})

            # 1. API OFICIAL: Obtenemos el nombre exacto del Artista
            api_artist = f"https://open.spotify.com/oembed?url={artist_url}"
            res_artist = requests.get(api_artist)
            if res_artist.status_code != 200:
                return JsonResponse({'valid': False, 'error': 'No se pudo verificar al artista en Spotify.'})
                
            main_artist_name = res_artist.json().get('title', '').strip().lower()

            # 2. API OFICIAL: Obtenemos el nombre oficial de la Canción
            api_track = f"https://open.spotify.com/oembed?url={track_url}"
            res_track = requests.get(api_track)
            if res_track.status_code != 200:
                return JsonResponse({'valid': False, 'error': 'No se pudo verificar la canción.'})
                
            track_name = res_track.json().get('title', 'Canción Desconocida')
            
            # 3. VALIDACIÓN INFALIBLE (Web Scraping): 
            # Spotify no da la lista de autores por API pública, así que leemos el código fuente 
            # de la canción para ver si el nombre del artista se menciona en alguna parte.
            track_page = requests.get(track_url)
            html_text = track_page.text.lower()
            
            # Sacamos la primera palabra del nombre del artista para ser flexibles (ej. The Beatles -> the)
            palabras_artista = main_artist_name.replace(',', '').split()
            palabra_clave = palabras_artista[0] if palabras_artista else ""

            if main_artist_name not in html_text and palabra_clave not in html_text:
                return JsonResponse({'valid': False, 'error': f'La canción "{track_name.title()}" no parece ser de {main_artist_name.title()}.'})

            return JsonResponse({
                'valid': True,
                'name': track_name,
                'duration': "🎵", # La API pública no da segundos exactos, usamos un ícono musical
                'url': track_url
            })
            
        except Exception as e:
            return JsonResponse({'valid': False, 'error': 'Error de conexión con Spotify.'})
            
    return JsonResponse({'valid': False, 'error': 'Método no permitido.'})

@login_required
def crear_playlist(request):
    if request.method == 'POST':
        form = PlaylistForm(request.POST, request.FILES)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.user = request.user
            playlist.save()
            return redirect('perfil_usuario', username=request.user.username)
    else:
        form = PlaylistForm()
    return render(request, 'music/crear_playlist.html', {'form': form, 'edit_mode': False})

@login_required
def validar_cancion_playlist(request):
    """Valida genéricamente cualquier canción de Spotify para la playlist"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            track_url = data.get('track_url', '')

            if not track_url or '/track/' not in track_url:
                return JsonResponse({'valid': False, 'error': 'Debes usar un enlace válido de una CANCIÓN de Spotify.'})

            api_track = f"https://open.spotify.com/oembed?url={track_url}"
            res_track = requests.get(api_track)
            
            if res_track.status_code != 200:
                return JsonResponse({'valid': False, 'error': 'No se pudo leer la canción en Spotify.'})
                
            track_name = res_track.json().get('title', 'Canción Desconocida')
            duration = res_track.json().get('duration', '🎵')
            
            # Limpiamos el nombre si viene con formato raro
            track_name = track_name.replace(' Spotify', '').strip()

            return JsonResponse({'valid': True, 'name': track_name, 'duration': duration, 'url': track_url})
        except Exception as e:
            return JsonResponse({'valid': False, 'error': 'Error de conexión.'})
    return JsonResponse({'valid': False, 'error': 'Método no permitido.'})
