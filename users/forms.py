from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django import forms
from .models import User, MusicianVerificationRequest
import re
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
# ==========================================
# 1. FORMULARIO DE REGISTRO (SIGNUP)
# ==========================================
class CustomUserCreationForm(UserCreationForm):
    
    # AQUÍ VAN LOS ERRORES DEL FORMULARIO (Como las contraseñas que no coinciden)
    error_messages = {
        'password_mismatch': "¡Percebes! Las contraseñas no son identicas unu. Vuelve a escribirlas con cuidado porfi uwu.",
    }

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
        
        labels = {
            'username': 'Tu nombre todo bonito uwu',
            'email': 'Tu Correo Electrónico porfi uwu',
        }
        help_texts = {
            'username': 'Máximo 150 caracteres. Solo letras, números y @/./+/-/_',
        }
        
        # AQUÍ VAN LOS ERRORES DE LA BASE DE DATOS (Cuando algo ya existe)
        error_messages = {
            'username': {
                'unique': "¡Demonios! Ese nombre todo bonito ya te lo ganaron unu. Elige otro porfi uwu.",
                'invalid': "¡Sin espacios porfi! uwu. Solo usa letritas, números o estos símbolos: @ . + - _",
            },
            'email': {
                'unique': "¡Repampanos! Ese correito ya está registrado unu. Usa uno nuevo o inicia sesión uwu.",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        password_fields = [field_name for field_name in self.fields if 'password' in field_name.lower()]
        
        if len(password_fields) > 0:
            first_pass = password_fields[0]
            self.fields[first_pass].label = "Contraseña super mega segura uwu"
            self.fields[first_pass].help_text = "Tu contraseña debe tener al menos 8 caracteres y ser muy segura uwu."
            
        if len(password_fields) > 1:
            second_pass = password_fields[1]
            self.fields[second_pass].label = "Confirma tu contraseña super mega segura uwu"
            self.fields[second_pass].help_text = "Escribela otra vez porfi uwu"

# ==========================================
# 2. FORMULARIO DE INICIO DE SESIÓN (LOGIN)
# ==========================================
class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Tu nombre todo bonito uwu",
        widget=forms.TextInput(attrs={'autofocus': True})
    )
    password = forms.CharField(
        label="Tu contraseña super mega segura uwu",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'})
    )
    
    error_messages = {
        'invalid_login': "¡Caracoles! Tus datos no coinciden unu. Revisa bien tu nombre o tu contraseña porfi.",
        'inactive': "Esta cuenta parece estar dormida unu.",
    }

class MusicianVerificationForm(forms.ModelForm):
    class Meta:
        model = MusicianVerificationRequest
        fields = ['spotify_artist_url', 'social_media_url']
        widgets = {
            'spotify_artist_url': forms.URLInput(attrs={'placeholder': 'Ej: https://open.spotify.com/artist/...'}),
            'social_media_url': forms.URLInput(attrs={'placeholder': 'Ej: https://instagram.com/tu_usuario'}),
        }

class MusicianVerificationForm(forms.ModelForm):
    class Meta:
        model = MusicianVerificationRequest
        fields = ['spotify_artist_url', 'social_media_url']
        widgets = {
            'spotify_artist_url': forms.URLInput(attrs={'placeholder': 'Ej: https://open.spotify.com/artist/...'}),
            'social_media_url': forms.URLInput(attrs={'placeholder': 'Tu perfil oficial de Instagram, X o Facebook'}),
        }

    # 1. VALIDACIÓN ESTRICTA DE SPOTIFY ARTISTA
    def clean_spotify_artist_url(self):
        url = self.cleaned_data.get('spotify_artist_url')
        
        # Comprobar que sea de spotify y que contenga /artist/
        if "spotify.com" not in url or "/artist/" not in url:
            raise forms.ValidationError(
                "¡Rayos! Este enlace no parece ser de un PERFIL DE ARTISTA. "
                "Asegúrate de que incluya '/artist/' en la URL porfi uwu."
            )
        return url

    # 2. VALIDACIÓN ESTRICTA DE REDES SOCIALES (SOLO PERFILES)
    def clean_social_media_url(self):
        url = self.cleaned_data.get('social_media_url').lower()
        
        # Definimos dominios permitidos
        dominios_validos = ['instagram.com', 'x.com', 'twitter.com', 'facebook.com']
        
        # Comprobar si pertenece a alguna red permitida
        if not any(dom in url for dom in dominios_validos):
            raise forms.ValidationError(
                "¡Ups! Solo aceptamos perfiles oficiales de Instagram, X (Twitter) o Facebook por seguridad unu."
            )

        # Filtro Anti-Contenido (Evitar videos, posts, reels, etc.)
        # Si la URL contiene patrones de contenido específico, lanzamos error
        patrones_prohibidos = [
            '/p/', '/reels/', '/tv/', '/stories/', # Instagram
            '/status/', '/i/events/',               # X / Twitter
            '/posts/', '/videos/', '/watch/', '/groups/' # Facebook
        ]

        if any(patron in url for patron in patrones_prohibidos):
            raise forms.ValidationError(
                "¡Oye! Has puesto un link a una publicación o video. "
                "Necesitamos el link directo a tu PERFIL principal porfi uwu."
            )

        return url

class ChangeEmailForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirma tu contraseña'}), label="Contraseña actual")
    class Meta:
        model = User
        fields = ['email']

# Formulario para eliminar cuenta
class DeleteAccountForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Escribe tu contraseña'}), label="Confirmar contraseña")
    confirmar = forms.BooleanField(label="Entiendo que esta acción es irreversible")

class EditProfileForm(forms.ModelForm):
    # Campo extra que no se guarda en la BD directamente, solo sirve para validar
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña actual', 'class': 'form-control'}),
        required=False, # Es falso porque solo se requiere SI cambia el username
        label="Contraseña actual",
        help_text="Requerida únicamente si deseas cambiar tu nombre de usuario."
    )

    class Meta:
        model = User
        fields = [
            'username', 'bio', 'profile_picture', 
            'instagram_url', 'x_url', 'facebook_url', 
            'tiktok_url', 'spotify_url', 'youtube_url'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Verificamos si el formulario tiene una instancia (un usuario cargado) 
        # y si ese usuario ya tiene el rol de músico
        if self.instance and self.instance.pk and getattr(self.instance, 'is_musician', False):
            
            # 1. Limpiamos cualquier espacio "fantasma" que traiga de la BD
            if self.instance.spotify_url:
                self.instance.spotify_url = self.instance.spotify_url.strip()

            # 2. ¡EL TRUCO!: Reemplazamos el URLField por un CharField en el formulario.
            # Esto destruye el validador estricto de URL de Django para esta vista.
            self.fields['spotify_url'] = forms.CharField(
                disabled=True,
                required=False,
                initial=self.instance.spotify_url,
                help_text="Como artista verificado, este enlace es permanente. Contacta a soporte si necesitas cambiarlo."
            )


    def clean(self):
        cleaned_data = super().clean()
        
        # --- BLINDAJE CONTRA EL ERROR DE URL DE SPOTIFY (MÚSICOS) ---
        if self.instance and getattr(self.instance, 'is_musician', False):
            # Aseguramos de que el dato limpio vaya sin espacios
            if self.instance.spotify_url:
                cleaned_data['spotify_url'] = self.instance.spotify_url.strip()

            # Si Django internamente guardó un error sobre spotify_url, lo aniquilamos
            if 'spotify_url' in self._errors:
                del self._errors['spotify_url']
        # ------------------------------------------------------------

        # --- NUEVA REGLA: OYENTES NO PUEDEN USAR LINKS DE ARTISTA ---
        nuevo_spotify_url = cleaned_data.get('spotify_url')
        es_musico = getattr(self.instance, 'is_musician', False)
        
        # Si el usuario escribió un link, y NO es músico (es decir, es oyente)
        if nuevo_spotify_url and not es_musico:
            # Revisamos si el link contiene la ruta de artista
            if '/artist/' in nuevo_spotify_url:
                # Lanzamos un error directamente debajo del campo de Spotify
                self.add_error('spotify_url', 'Como oyente, solo puedes enlazar un perfil de usuario. Los enlaces de artista son exclusivos para músicos.')
        # ------------------------------------------------------------

        new_username = cleaned_data.get('username')
        current_password = cleaned_data.get('current_password')

        # Verificamos si el usuario está intentando cambiar su username original
        if self.instance.username != new_username:
            # 1. Verificamos que haya escrito una contraseña
            if not current_password:
                self.add_error('current_password', 'Debes ingresar tu contraseña actual para autorizar el cambio de nombre de usuario.')
            
            # 2. Verificamos que la contraseña sea la correcta usando el método nativo de Django
            elif not self.instance.check_password(current_password):
                self.add_error('current_password', 'La contraseña ingresada es incorrecta. No se ha cambiado el nombre de usuario.')

        return cleaned_data