from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Max
from itertools import chain
from operator import attrgetter
import requests

# IMPORTACIONES DE MODELOS Y FORMULARIOS (Todos completos)
from .models import Review, Reaction, Comment, CommentReaction, ConcertLog, IdealConcert
from .forms import ReviewForm, ConcertLogForm, IdealConcertForm


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
    
    # Unimos las TRES listas
    publicaciones = sorted(chain(resenas, conciertos, ideales), key=attrgetter('created_at'), reverse=True)

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
    
    if request.method == 'POST' and request.user == obj.user:
        nuevo_texto = request.POST.get('texto')
        if nuevo_texto:
            if tipo_pub == 'resena': obj.text = nuevo_texto
            elif tipo_pub == 'concierto': obj.resena = nuevo_texto
            # El concierto ideal no tiene un campo simple de texto para editar
            obj.save()
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest': 
            return JsonResponse({'success': True, 'text': nuevo_texto})
    return redirect('feed')

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
    else: obj = comentario.ideal_concert
    
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
