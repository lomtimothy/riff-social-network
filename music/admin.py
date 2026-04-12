from django.contrib import admin
from .models import Artist, Album, Song, Review, ConcertLog, IdealConcert, Playlist, NoticeBoard, UpcomingConcert

# --- Catálogo Musical ---
@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'spotify_url', 'user_musician')
    search_fields = ('name',)

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist')
    search_fields = ('title', 'artist__name')
    list_filter = ('artist',)

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'album')
    search_fields = ('title', 'artist__name')
    list_filter = ('artist',)

# --- Interacciones ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

# --- ESTA FUE LA PARTE QUE CAMBIAMOS PARA QUE COINCIDA CON EL MODELO ---
@admin.register(ConcertLog)
class ConcertLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'artista', 'lugar', 'ciudad', 'fecha_concierto', 'created_at')
    list_filter = ('fecha_concierto', 'ciudad')
    search_fields = ('artista', 'lugar', 'ciudad', 'user__username')

@admin.register(IdealConcert)
class IdealConcertAdmin(admin.ModelAdmin):
    # Usamos los nuevos nombres en español
    list_display = ('user', 'artista', 'lugar', 'pais', 'created_at')
@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    # Usamos los nuevos nombres en español
    list_display = ('user', 'titulo', 'created_at')

# --- Módulos de Músicos ---
@admin.register(NoticeBoard)
class NoticeBoardAdmin(admin.ModelAdmin):
    list_display = ('musician', 'created_at')

@admin.register(UpcomingConcert)
class UpcomingConcertAdmin(admin.ModelAdmin):
    list_display = ('musician', 'venue', 'city', 'date')