from django import forms
from django.core.exceptions import ValidationError # <-- IMPORTANTE: Agregar esto arriba
from .models import Review
from .models import ConcertLog
from django.utils import timezone

class ReviewForm(forms.ModelForm):
    spotify_url = forms.URLField(
        label="Enlace de Spotify",
        required=True,
        widget=forms.URLInput(attrs={
            'placeholder': 'https://open.spotify.com/track/...',
            'style': 'width: 100%; padding: 10px; background: black; border: 1px solid var(--neon-cyan); color: var(--neon-cyan); font-family: "Orbitron", sans-serif; box-sizing: border-box;'
        })
    )

    class Meta:
        model = Review
        fields = ['spotify_url', 'rating', 'text']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'min': 0, 'max': 5, 
                'placeholder': '0 a 5 estrellas',
                'style': 'width: 100%; padding: 10px; background: black; border: 1px solid var(--neon-cyan); color: var(--neon-cyan); font-family: "Orbitron", sans-serif; box-sizing: border-box;'
            }),
            'text': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': '¡Escribe tu reseña aquí! UWU',
                'style': 'width: 100%; padding: 10px; background: black; border: 1px solid var(--neon-cyan); color: var(--neon-cyan); font-family: "Orbitron", sans-serif; box-sizing: border-box;'
            }),
        }

    # NUEVO: Validación estricta del enlace
    def clean_spotify_url(self):
        url = self.cleaned_data.get('spotify_url')
        if url:
            # 1. Bloqueamos explícitamente podcasts y shows
            if '/episode/' in url or '/show/' in url:
                raise ValidationError("¡Oye! RIFF es solo para música. No se aceptan enlaces de podcasts unu")
            
            # 2. Nos aseguramos de que SOLO contenga entidades musicales válidas
            entidades_permitidas = ['/track/', '/album/', '/artist/', '/playlist/']
            if not any(entidad in url for entidad in entidades_permitidas):
                raise ValidationError("Enlace no válido. Asegúrate de que sea una Canción, Álbum, Artista o Playlist.")
                
        return url
        
class ConcertLogForm(forms.ModelForm):
    class Meta:
        model = ConcertLog
        fields = ['enlace_spotify', 'lugar', 'pais', 'estado', 'ciudad', 'fecha_concierto', 'resena', 'imagen']
        widgets = {
            'fecha_concierto': forms.DateInput(attrs={'type': 'date'}),
            'pais': forms.HiddenInput(attrs={'id': 'real_pais'}),
            'estado': forms.HiddenInput(attrs={'id': 'real_estado'}),
            'ciudad': forms.HiddenInput(attrs={'id': 'real_ciudad'}),
        }

    # Validación del enlace de Spotify (Ya la tenías)
    def clean_enlace_spotify(self):
        url = self.cleaned_data.get('enlace_spotify')
        if url and '/artist/' not in url:
            raise ValidationError("¡Oye! Para registrar un concierto, el enlace DEBE ser el perfil del Artista.")
        return url

    # NUEVO: Validación lógica de la fecha
    def clean_fecha_concierto(self):
        fecha = self.cleaned_data.get('fecha_concierto')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("¡Oye! No puedes registrar un concierto que aún no ha sucedido. RIFF no es una máquina del tiempo unu.")
        return fecha