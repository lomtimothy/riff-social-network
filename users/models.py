from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Roles
    email = models.EmailField(unique=True, blank=False, null=False, verbose_name='Correo Electrónico')
    is_listener = models.BooleanField(default=True, verbose_name='Es Oyente')
    is_musician = models.BooleanField(default=False, verbose_name='Es Músico')

    # Privacidad y Red Social
    is_private = models.BooleanField(default=False, verbose_name='Perfil Privado')
    friends = models.ManyToManyField('self', symmetrical=True, blank=True, verbose_name='Amigos')

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