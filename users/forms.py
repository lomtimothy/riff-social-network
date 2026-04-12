from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django import forms
from .models import User, MusicianVerificationRequest

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