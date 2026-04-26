from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone # <-- Importante
from django.core.exceptions import ValidationError # <-- Importante

# 1. VALIDADOR GLOBAL DE SPOTIFY
spotify_validator = RegexValidator(
    regex=r'^https:\/\/(open\.spotify\.com|play\.spotify\.com)\/.*$',
    message="El enlace debe ser una URL válida de Spotify."
)

# ==========================================
# ENTIDADES MUSICALES (Catálogo Base)
# ==========================================

class Artist(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Artista")
    spotify_url = models.URLField(validators=[spotify_validator], unique=True, verbose_name="Enlace de Spotify")
    
    user_musician = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'is_musician': True}, related_name='artist_profile'
    )

    def __str__(self):
        return self.name

class Album(models.Model):
    title = models.CharField(max_length=255, verbose_name="Título del Álbum")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums')
    spotify_url = models.URLField(validators=[spotify_validator], unique=True)
    image_url = models.URLField(null=True, blank=True) # <-- Agregar este
    author_notes = models.TextField(blank=True, null=True, verbose_name="Notas del autor (Solo Músicos)")
    created_at = models.DateTimeField(auto_now_add=True) # Para ordenarlos

    def __str__(self):
        return f"{self.title} - {self.artist.name}"

class Song(models.Model):
    title = models.CharField(max_length=255, verbose_name="Título de la Canción")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='songs')
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name='songs')
    spotify_url = models.URLField(validators=[spotify_validator], unique=True)

    def __str__(self):
        return self.title

# ==========================================
# MÓDULOS DE INTERACCIÓN (Oyentes y Músicos)
# ==========================================

class Review(models.Model):
    """Módulo de Reseñas y Calificación"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    
    song = models.ForeignKey(Song, on_delete=models.CASCADE, null=True, blank=True)
    album = models.ForeignKey(Album, on_delete=models.CASCADE, null=True, blank=True)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, null=True, blank=True)
    
    rating = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)], verbose_name="Estrellas (0-5)")
    text = models.TextField(verbose_name="Reseña")
    created_at = models.DateTimeField(auto_now_add=True)
    spotify_url = models.URLField(validators=[spotify_validator], null=True, blank=True)
    entity_name = models.CharField(max_length=255, null=True, blank=True)
    entity_type = models.CharField(max_length=50, null=True, blank=True) 
    image_url = models.URLField(null=True, blank=True) 
    
    @property
    def likes_count(self):
        return self.reactions.filter(reaction_type='LIKE').count()

    @property
    def dislikes_count(self):
        return self.reactions.filter(reaction_type='DISLIKE').count()

def validar_fecha_no_futura(value):
    if value > timezone.now().date():
        raise ValidationError('La fecha del concierto no puede ser en el futuro.')

class ConcertLog(models.Model):
    """Módulo de Bitácora: Mis Conciertos"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='concert_logs')
    artista = models.CharField(max_length=255, help_text="Nombre del artista principal")
    enlace_spotify = models.URLField(max_length=500, validators=[spotify_validator], help_text="Enlace de Spotify del artista para validación")
    imagen_artista = models.URLField(max_length=500, null=True, blank=True, help_text="Foto oficial del artista desde Spotify")
    
    lugar = models.CharField(max_length=255, help_text="Nombre del recinto (Venue)")
    pais = models.CharField(max_length=255, default="Desconocido", help_text="País del evento")
    estado = models.CharField(max_length=255, default="Desconocido", help_text="Estado o Provincia")
    ciudad = models.CharField(max_length=255)
    
    # 2. Aplicamos el validador aquí
    fecha_concierto = models.DateField(
        validators=[validar_fecha_no_futura], 
        help_text="¿Cuándo fue el evento?"
    )
    
    resena = models.TextField(help_text="Reseña de tu experiencia")
    imagen = models.ImageField(upload_to='conciertos/', blank=True, null=True, help_text="Evidencia fotográfica (Opcional)")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def likes_count(self):
        return self.reactions.filter(reaction_type='LIKE').count()

    @property
    def dislikes_count(self):
        return self.reactions.filter(reaction_type='DISLIKE').count()

    def __str__(self):
        return f"{self.artista} en {self.lugar} - {self.user.username}"

# ==========================================
# MÓDULOS DE DIFUSIÓN (Exclusivo Músicos)
# ==========================================

class Reaction(models.Model):
    REACTION_CHOICES = (('LIKE', 'Me gusta'), ('DISLIKE', 'No me gusta'))
    review = models.ForeignKey('Review', on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)
    concert = models.ForeignKey('ConcertLog', on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)
    ideal_concert = models.ForeignKey('IdealConcert', on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)
    # NUEVO:
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)
    
    announcement = models.ForeignKey('Announcement', on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)
    upcoming_concert = models.ForeignKey('UpcomingConcert', on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)

class Comment(models.Model):
    review = models.ForeignKey('Review', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    concert = models.ForeignKey('ConcertLog', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    ideal_concert = models.ForeignKey('IdealConcert', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    # NUEVO:
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)

    announcement = models.ForeignKey('Announcement', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    upcoming_concert = models.ForeignKey('UpcomingConcert', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.CharField(max_length=255, verbose_name="Comentario")
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')

    @property
    def likes_count(self): return self.reactions.filter(reaction_type='LIKE').count()
    @property
    def dislikes_count(self): return self.reactions.filter(reaction_type='DISLIKE').count()
    @property
    def is_reply(self): return self.parent is not None

class CommentReaction(models.Model):
    """Me Gusta / No Me Gusta para COMENTARIOS"""
    REACTION_CHOICES = (
        ('LIKE', 'Me gusta'),
        ('DISLIKE', 'No me gusta')
    )
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)

    class Meta:
        unique_together = ('comment', 'user')

class IdealConcert(models.Model):
    """Módulo de Simulación: Mi Concierto Ideal"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ideal_concerts')
    artista = models.CharField(max_length=255)
    enlace_spotify = models.URLField(max_length=500)
    imagen_artista = models.URLField(max_length=500, null=True, blank=True)
    
    lugar = models.CharField(max_length=255, help_text="El Venue de tus sueños")
    pais = models.CharField(max_length=255)
    estado = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=255)
    
    setlist = models.TextField(help_text="Lista de canciones en formato JSON")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def likes_count(self):
        return self.reactions.filter(reaction_type='LIKE').count()

    @property
    def dislikes_count(self):
        return self.reactions.filter(reaction_type='DISLIKE').count()

    # Función mágica para leer el JSON en el HTML
    def get_setlist_array(self):
        import json
        try:
            return json.loads(self.setlist)
        except:
            return []

class Playlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='playlists')
    titulo = models.CharField(max_length=255, verbose_name="Título de la Playlist")
    resena = models.TextField(verbose_name="¿De qué trata esta playlist?")
    imagen = models.ImageField(upload_to='playlists/', null=True, blank=True, verbose_name="Portada (Opcional)")
    canciones = models.TextField(help_text="Lista de canciones en formato JSON")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def likes_count(self):
        return self.reactions.filter(reaction_type='LIKE').count()

    @property
    def dislikes_count(self):
        return self.reactions.filter(reaction_type='DISLIKE').count()

    def get_canciones_array(self):
        import json
        try:
            return json.loads(self.canciones)
        except:
            return []

class Announcement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    titulo = models.CharField(max_length=255, verbose_name="Título del Aviso")
    mensaje = models.TextField(verbose_name="Mensaje oficial para tus fans")
    imagen = models.ImageField(upload_to='announcements/', null=True, blank=True, verbose_name="Imagen adjunta (Opcional)")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def likes_count(self): return self.reactions.filter(reaction_type='LIKE').count()
    @property
    def dislikes_count(self): return self.reactions.filter(reaction_type='DISLIKE').count()

class UpcomingConcert(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='upcoming_concerts')
    nombre_tour = models.CharField(max_length=255, verbose_name="Nombre del Tour o Evento")
    lugar = models.CharField(max_length=255, verbose_name="Venue / Lugar")
    ciudad = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    pais = models.CharField(max_length=100)
    fecha = models.DateField(verbose_name="Fecha del Evento")
    link_boletos = models.URLField(null=True, blank=True, verbose_name="Link para comprar boletos (Opcional)")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def likes_count(self): return self.reactions.filter(reaction_type='LIKE').count()
    @property
    def dislikes_count(self): return self.reactions.filter(reaction_type='DISLIKE').count()