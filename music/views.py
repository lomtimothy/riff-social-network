from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Review, Reaction, Comment, CommentReaction
from .forms import ReviewForm
import requests # <--- IMPORTANTE AGREGAR ESTO AL INICIO
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Max
from django.db.models import Q, Max
from .forms import ConcertLogForm
from itertools import chain
from operator import attrgetter
from .models import ConcertLog # <-- Asegúrate de importar el modelo

@login_required
def feed_principal(request):
    amigos = request.user.friends.all()
    
    # 1. Obtenemos las reseñas y les ponemos una etiqueta
    resenas = list(Review.objects.filter(Q(user__in=amigos) | Q(user=request.user)))
    for r in resenas: r.tipo_pub = 'resena'
              
    # 2. Obtenemos los conciertos y les ponemos una etiqueta
    conciertos = list(ConcertLog.objects.filter(Q(user__in=amigos) | Q(user=request.user)))
    for c in conciertos: c.tipo_pub = 'concierto'
    
    # 3. Unimos ambas listas y las ordenamos por fecha de creación (de más nuevo a más viejo)
    publicaciones = sorted(chain(resenas, conciertos), key=attrgetter('created_at'), reverse=True)

    amigos_activos = amigos.annotate(
        ultima_actividad=Max('reviews__created_at')
    ).order_by('-ultima_actividad')
              
    return render(request, 'music/feed.html', {
        'publicaciones': publicaciones, # <-- Enviamos la lista fusionada
        'amigos_activos': amigos_activos 
    })

@login_required
def crear_resena(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            nueva_resena = form.save(commit=False)
            nueva_resena.user = request.user
            
            # --- CONEXIÓN CON LA API DE SPOTIFY ---
            # 1. Sacamos el link que pegó el usuario
            spotify_link = form.cleaned_data.get('spotify_url')
            
            if spotify_link:
                # 2. Detectamos qué es leyendo la URL
                if '/track/' in spotify_link: tipo = 'Canción 🎵'
                elif '/album/' in spotify_link: tipo = 'Álbum 💿'
                elif '/artist/' in spotify_link: tipo = 'Artista 🎤'
                elif '/playlist/' in spotify_link: tipo = 'Playlist 🎧'
                else: tipo = 'Entidad Musical 🎶'
                
                # 3. Le pedimos la foto y el título a Spotify
                api_url = f"https://open.spotify.com/oembed?url={spotify_link}"
                try:
                    respuesta = requests.get(api_url).json()
                    nueva_resena.entity_name = respuesta.get('title', 'Título Desconocido')
                    nueva_resena.image_url = respuesta.get('thumbnail_url', '')
                    nueva_resena.entity_type = tipo
                    nueva_resena.spotify_url = spotify_link
                except:
                    # Si Spotify falla, guardamos datos por defecto
                    nueva_resena.entity_name = "Enlace de Spotify"
                    nueva_resena.entity_type = tipo

            nueva_resena.save()
            return redirect('feed')
    else:
        form = ReviewForm()
    
    return render(request, 'music/crear_resena.html', {'form': form})
@login_required
def reaccionar(request, tipo_pub, id, tipo):
    obj = get_object_or_404(Review, id=id) if tipo_pub == 'resena' else get_object_or_404(ConcertLog, id=id)
    kwargs = {'review': obj} if tipo_pub == 'resena' else {'concert': obj}
    
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
        obj = get_object_or_404(Review, id=id) if tipo_pub == 'resena' else get_object_or_404(ConcertLog, id=id)
            
        if texto:
            parent_obj = get_object_or_404(Comment, id=parent_id) if parent_id else None
            kwargs = {'review': obj} if tipo_pub == 'resena' else {'concert': obj}
            nuevo_comentario = Comment.objects.create(user=request.user, text=texto, parent=parent_obj, **kwargs)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                html = render_to_string('music/comentario_recursivo.html', {'comentario': nuevo_comentario, 'objeto': obj, 'tipo_pub': tipo_pub}, request=request)
                return JsonResponse({'html': html, 'parent_id': parent_id, 'comments_count': obj.comments.count()})
    return redirect('feed')

@login_required
def eliminar_comentario(request, comentario_id):
    comentario = get_object_or_404(Comment, id=comentario_id)
    resena = comentario.review # Guardamos la reseña para actualizar el contador
    
    if request.user == comentario.user:
        comentario.delete()
        
    # LA MAGIA AJAX: Devolvemos éxito y el nuevo total de comentarios
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'comments_count': resena.comments.count()
        })
        
    return redirect('feed')

@login_required
def editar_comentario(request, comentario_id):
    comentario = get_object_or_404(Comment, id=comentario_id)
    
    if request.method == 'POST':
        nuevo_texto = request.POST.get('texto')
        if nuevo_texto and request.user == comentario.user:
            comentario.text = nuevo_texto
            comentario.save()
            
        # LA MAGIA AJAX PARA EDITAR: Devolvemos el nuevo texto
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
        if reaccion.reaction_type == tipo:
            reaccion.delete()
        else:
            reaccion.reaction_type = tipo
            reaccion.save()
            
    # LA MAGIA AJAX PARA LIKES DE COMENTARIOS
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'likes': comentario.likes_count,
            'dislikes': comentario.dislikes_count
        })
        
    return redirect('feed')

@login_required
def agregar_concierto(request):
    if request.method == 'POST':
        form = ConcertLogForm(request.POST, request.FILES)
        if form.is_valid():
            concierto = form.save(commit=False)
            concierto.user = request.user
            
            # --- MAGIA DE AUTOMATIZACIÓN ---
            # 1. Extraemos el enlace válido que puso el usuario
            spotify_link = form.cleaned_data.get('enlace_spotify')
            
            # 2. Consultamos la API oculta para obtener la info
            api_url = f"https://open.spotify.com/oembed?url={spotify_link}"
            try:
                respuesta = requests.get(api_url).json()
                # Spotify nos devolverá el nombre del artista en el 'title'
                nombre_artista = respuesta.get('title', 'Artista Desconocido')
                concierto.artista = nombre_artista
            except:
                # Plan de respaldo si falla el internet o la API
                concierto.artista = "Artista Desconocido"
            # ------------------------------
            
            concierto.save()
            return redirect('perfil_usuario', username=request.user.username)
    else:
        form = ConcertLogForm()
        
    return render(request, 'music/crear_concierto.html', {'form': form})

@login_required
def eliminar_publicacion(request, tipo_pub, id):
    obj = get_object_or_404(Review, id=id) if tipo_pub == 'resena' else get_object_or_404(ConcertLog, id=id)
    if request.user == obj.user: obj.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return JsonResponse({'success': True})
    return redirect('feed')

@login_required
def editar_publicacion(request, tipo_pub, id):
    obj = get_object_or_404(Review, id=id) if tipo_pub == 'resena' else get_object_or_404(ConcertLog, id=id)
    if request.method == 'POST' and request.user == obj.user:
        nuevo_texto = request.POST.get('texto')
        if nuevo_texto:
            if tipo_pub == 'resena': obj.text = nuevo_texto
            else: obj.resena = nuevo_texto
            obj.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return JsonResponse({'success': True, 'text': nuevo_texto})
    return redirect('feed')
