from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import secrets

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
    instagram_url = models.URLField(blank=True, null=True, verbose_name='Instagram')
    x_url = models.URLField(blank=True, null=True, verbose_name='X (Twitter)')

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
    Si apruebas, da poderes. Si rechazas o pones pendiente, los quita.
    """
    user = instance.user
    
    if instance.status == 'APPROVED':
        # 1. Le damos el poder de músico
        if not user.is_musician:
            user.is_musician = True
            user.is_listener = False # APAGAMOS el rol de oyente
            user.is_private = False  # Lo obligamos a ser público
            user.save()
            
    elif instance.status in ['PENDING', 'REJECTED']:
        # 2. Si te arrepientes o lo rechazas, le quitamos los poderes
        if user.is_musician:
            user.is_musician = False
            user.is_listener = True  # VUELVE a ser un oyente normal
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