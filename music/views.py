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
def reaccionar(request, resena_id, tipo):
    resena = get_object_or_404(Review, id=resena_id)
    
    reaccion, created = Reaction.objects.get_or_create(
        review=resena, user=request.user, defaults={'reaction_type': tipo}
    )
    
    if not created:
        if reaccion.reaction_type == tipo:
            reaccion.delete() 
        else:
            reaccion.reaction_type = tipo
            reaccion.save()
            
    # LA MAGIA AJAX: Si la petición viene de nuestro script de JavaScript, devolvemos JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'likes': resena.likes_count,
            'dislikes': resena.dislikes_count
        })
            
    return redirect('feed')

@login_required
def comentar(request, resena_id):
    if request.method == 'POST':
        resena = get_object_or_404(Review, id=resena_id)
        texto = request.POST.get('comentario')
        parent_id = request.POST.get('parent_id') 
        
        if texto:
            parent_obj = None
            if parent_id:
                parent_obj = get_object_or_404(Comment, id=parent_id)
            
            # 1. Creamos el comentario en la base de datos
            nuevo_comentario = Comment.objects.create(review=resena, user=request.user, text=texto, parent=parent_obj)
            
            # 2. LA MAGIA AJAX: Si es una petición secreta, renderizamos el HTML y lo devolvemos
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                html = render_to_string('music/comentario_recursivo.html', {'comentario': nuevo_comentario, 'resena': resena}, request=request)
                return JsonResponse({
                    'html': html, 
                    'parent_id': parent_id, 
                    'comments_count': resena.comments.count()
                })
            
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
def eliminar_resena(request, resena_id):
    resena = get_object_or_404(Review, id=resena_id)
    
    # Solo el autor puede eliminarla
    if request.user == resena.user:
        resena.delete()
        
    # Magia AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
        
    return redirect('feed')

@login_required
def editar_resena(request, resena_id):
    resena = get_object_or_404(Review, id=resena_id)
    
    if request.method == 'POST' and request.user == resena.user:
        nuevo_texto = request.POST.get('texto')
        if nuevo_texto:
            resena.text = nuevo_texto
            resena.save()
            
        # Magia AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'text': nuevo_texto})
            
    return redirect('feed')

@login_required
def agregar_concierto(request):
    if request.method == 'POST':
        # Al ser un formulario con imágenes, necesitamos pasar request.FILES
        form = ConcertLogForm(request.POST, request.FILES)
        if form.is_valid():
            # Guardamos el formulario, pero pausamos un segundo con commit=False
            concierto = form.save(commit=False)
            # Le asignamos el usuario que está conectado
            concierto.user = request.user
            # Ahora sí, ¡a la base de datos!
            concierto.save()
            # Redirigimos al perfil del usuario
            return redirect('perfil_usuario', username=request.user.username)
    else:
        form = ConcertLogForm()
        
    return render(request, 'music/crear_concierto.html', {'form': form})
