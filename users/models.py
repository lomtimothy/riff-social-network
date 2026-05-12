from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import secrets
from django.core.validators import RegexValidator

class User(AbstractUser):
    # Roles
    email = models.EmailField(unique=True, blank=False, null=False, verbose_name='Correo Electrónico')
    is_listener = models.BooleanField(default=True, verbose_name='Es Oyente')
    is_musician = models.BooleanField(default=False, verbose_name='Es Músico')

    # Privacidad y Red Social
    is_private = models.BooleanField(default=False, verbose_name='Perfil Privado')
    friends = models.ManyToManyField('self', symmetrical=True, blank=True, verbose_name='Amigos')
    two_factor_login = models.BooleanField(default=True, verbose_name="2FA activado para login")
    # Identidad Visual
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name='Foto de Perfil')
    bio = models.CharField(max_length=150, blank=True, null=True, verbose_name='Biografía')
    instagram_regex = RegexValidator(
        regex=r'^https?:\/\/(www\.)?instagram\.com\/[a-zA-Z0-9_.]+\/?(\?.*)?$',
        message='Ingresa un enlace de perfil válido (ej. https://instagram.com/usuario). No se permiten links a fotos/reels.'
    )
    x_regex = RegexValidator(
        regex=r'^https?:\/\/(www\.)?(twitter\.com|x\.com)\/[a-zA-Z0-9_]+\/?(\?.*)?$',
        message='Ingresa un enlace de perfil de X/Twitter válido (ej. https://x.com/usuario). No se permiten links a tweets.'
    )
    facebook_regex = RegexValidator(
        # Agregamos (share\/)? para que el segmento "share/" sea opcional
        # y mantenemos (\?.*)? al final para los parámetros de rastreo
        regex=r'^https?:\/\/(www\.)?facebook\.com\/(share\/)?[a-zA-Z0-9.]+\/?(\?.*)?$',
        message='Ingresa un enlace de perfil de Facebook válido o un enlace compartido.'
    )
    tiktok_regex = RegexValidator(
        # Añadimos (\?.*)? al final justo antes del $
        regex=r'^https?:\/\/(www\.)?tiktok\.com\/@[a-zA-Z0-9_.]+\/?(\?.*)?$',
        message='Ingresa un enlace de perfil de TikTok válido. Debe incluir el "@" (ej. https://tiktok.com/@usuario).'
    )
    spotify_regex = RegexValidator(
        # Añadimos (intl-[a-zA-Z]{2}\/)? para aceptar el formato internacional de forma opcional
        regex=r'^https?:\/\/open\.spotify\.com\/(intl-[a-zA-Z]{2}\/)?(user|artist)\/[a-zA-Z0-9]+\/?(\?.*)?$',
        message='Ingresa un enlace de usuario o artista de Spotify válido. No se permiten links a canciones o playlists.'
    )
    youtube_regex = RegexValidator(
        regex=r'^https?:\/\/(www\.)?youtube\.com\/(c\/|channel\/|@)[a-zA-Z0-9_-]+\/?(\?.*)?$',
        message='Ingresa un canal de YouTube válido (ej. https://youtube.com/@canal). No se permiten links a videos.'
    )

    # Aplicamos los validadores a los campos
    instagram_url = models.URLField(max_length=200, blank=True, null=True, validators=[instagram_regex])
    x_url = models.URLField(max_length=200, blank=True, null=True, validators=[x_regex])
    facebook_url = models.URLField(max_length=200, blank=True, null=True, validators=[facebook_regex])
    tiktok_url = models.URLField(max_length=200, blank=True, null=True, validators=[tiktok_regex])
    spotify_url = models.URLField(max_length=200, blank=True, null=True, validators=[spotify_regex])
    youtube_url = models.URLField(max_length=200, blank=True, null=True, validators=[youtube_regex])
    last_viewed_requests = models.DateTimeField(null=True, blank=True, verbose_name="Última vez que vio solicitudes")
    last_viewed_suggestions = models.DateTimeField(null=True, blank=True, verbose_name="Última vez que vio sugerencias")
    def save(self, *args, **kwargs):
        # Regla de negocio: Los perfiles de músicos serán públicos siempre
        if self.is_musician:
            self.is_private = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {'Músico' if self.is_musician else 'Oyente'}"


class FriendRequest(models.Model):
    """Modelo para gestionar el envío y estado de las solicitudes de amistad"""
    sender = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE, verbose_name="Remitente")
    receiver = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE, verbose_name="Destinatario")
    is_active = models.BooleanField(default=True, verbose_name="Solicitud Pendiente")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de envío")

    class Meta:
        # Evita que un usuario envíe múltiples solicitudes a la misma persona
        unique_together = ('sender', 'receiver')
        verbose_name = 'Solicitud de Amistad'
        verbose_name_plural = 'Solicitudes de Amistad'

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}"

class MusicianVerificationRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification_request')
    spotify_artist_url = models.URLField(verbose_name="Enlace de tu Perfil de Artista en Spotify")
    social_media_url = models.URLField(verbose_name="Enlace a tu Instagram o X (Para verificar identidad)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Verificación de {self.user.username} - {self.status}"


@receiver(post_save, sender=MusicianVerificationRequest)
def actualizar_rol_musico(sender, instance, **kwargs):
    """
    Vigila los cambios en las solicitudes. 
    Si apruebas, da poderes y SOBREESCRIBE el link de Spotify con el de artista. 
    Si rechazas o pones pendiente, quita poderes y respeta el link original.
    """
    user = instance.user
    
    if instance.status == 'APPROVED':
        # 1. Le damos el poder de músico
        user.is_musician = True
        user.is_listener = False # APAGAMOS el rol de oyente
        user.is_private = False  # Lo obligamos a ser público
        
        # 2. ACTUALIZACIÓN AUTOMÁTICA DEL LINK
        # Al quitar el "if not user.spotify_url", forzamos a que el link de 
        # artista Pise/Sobreescriba cualquier link de oyente que tuviera antes.
        # NOTA: Usamos .strip() por seguridad para evitar el error de los espacios en blanco.
        if instance.spotify_artist_url:
            user.spotify_url = instance.spotify_artist_url.strip()
            
        # 3. Guardamos los cambios en el perfil del usuario
        user.save()

        from music.models import Artist # Importamos aquí para evitar errores circulares
        Artist.objects.get_or_create(
            user_musician=user,
            defaults={
                'name': user.username,
                'spotify_url': user.spotify_url
            }
        )
            
    elif instance.status in ['PENDING', 'REJECTED']:
        # 4. Si la solicitud es rechazada (o devuelta a pendiente), revertimos roles
        if user.is_musician:
            user.is_musician = False
            user.is_listener = True  # VUELVE a ser un oyente normal
            
            # OJO AQUÍ: No escribimos ninguna línea de código relacionada con `user.spotify_url`.
            # Al ignorar ese campo, Django simplemente no lo modifica al hacer el .save().
            # Por lo tanto, si el usuario tenía un link de oyente antes de hacer la solicitud,
            # ese link permanecerá ahí sano y salvo.
            
            user.save()
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at'] # Los más viejos arriba, los nuevos abajo (como WhatsApp)

    def __str__(self):
        return f"De {self.sender.username} a {self.receiver.username}"

# MODELO PARA LA AUTENTICACIÓN EN DOS PASOS (2FA)
class UserOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp')
    code = models.CharField(max_length=6, blank=True, null=True)

    def generate_code(self):
        # Genera un número aleatorio y criptográficamente seguro de 6 dígitos
        self.code = str(secrets.randbelow(900000) + 100000) 
        self.save()
        return self.code