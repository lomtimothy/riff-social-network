# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from music.models import Reaction, Comment, CommentReaction
from .models import Notification

@receiver(post_save, sender=Reaction)
def notify_reaction(sender, instance, created, **kwargs):
    if created:
        # Buscamos quién es el dueño del post (review, concert, etc.)
        target = instance.review or instance.concert or instance.album or instance.playlist or instance.announcement or instance.upcoming_concert or instance.ideal_concert
        
        if target and target.user != instance.user:
            # Traducimos el tipo de reacción para que sea más amigable de leer
            tipo_reaccion = "❤️ Me gusta" if instance.reaction_type == 'LIKE' else "💔 No me gusta"
            
            Notification.objects.create(
                recipient=target.user,
                actor=instance.user,
                verb=f'reaccionó con {tipo_reaccion} a tu publicación',
                target_content_object=target
            )

@receiver(post_save, sender=Comment)
def notify_comment(sender, instance, created, **kwargs):
    if created:
        # Cortamos el comentario a 30 caracteres para el aviso
        snippet = (instance.text[:30] + '...') if len(instance.text) > 30 else instance.text
        
        # Si es una respuesta a otro comentario
        if instance.parent and instance.parent.user != instance.user:
            Notification.objects.create(
                recipient=instance.parent.user,
                actor=instance.user,
                verb=f'respondió a tu comentario: "{snippet}"',
                target_content_object=instance.parent
            )
        # Si es un comentario en un post principal
        else:
            target = instance.review or instance.concert or instance.album or instance.playlist or instance.announcement or instance.upcoming_concert or instance.ideal_concert
            if target and target.user != instance.user:
                # Determinamos el tipo de publicación si lo tiene, si no, usamos 'publicación'
                tipo_pub = instance.entity_type if hasattr(instance, 'entity_type') else 'publicación'
                
                Notification.objects.create(
                    recipient=target.user,
                    actor=instance.user,
                    verb=f'comentó en tu {tipo_pub}: "{snippet}"',
                    target_content_object=target
                )

@receiver(post_save, sender=CommentReaction)
def notify_comment_reaction(sender, instance, created, **kwargs):
    if created and instance.comment.user != instance.user:
        # Cortamos el comentario original al que le dieron like para darle contexto
        snippet = (instance.comment.text[:30] + '...') if len(instance.comment.text) > 30 else instance.comment.text
        tipo_reaccion = "❤️ Me gusta" if instance.reaction_type == 'LIKE' else "💔 No me gusta"

        Notification.objects.create(
            recipient=instance.comment.user,
            actor=instance.user,
            verb=f'reaccionó con {tipo_reaccion} a tu comentario: "{snippet}"',
            target_content_object=instance.comment
        )