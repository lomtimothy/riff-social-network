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
            Notification.objects.create(
                recipient=target.user,
                actor=instance.user,
                verb=f"reaccionó a tu {instance.reaction_type.lower()} en su publicación",
                target_content_object=target
            )

@receiver(post_save, sender=Comment)
def notify_comment(sender, instance, created, **kwargs):
    if created:
        # Si es una respuesta a otro comentario
        if instance.parent and instance.parent.user != instance.user:
            Notification.objects.create(
                recipient=instance.parent.user,
                actor=instance.user,
                verb="respondió a tu comentario",
                target_content_object=instance.parent
            )
        # Si es un comentario en un post
        else:
            target = instance.review or instance.concert or instance.album or instance.playlist or instance.announcement or instance.upcoming_concert or instance.ideal_concert
            if target and target.user != instance.user:
                Notification.objects.create(
                    recipient=target.user,
                    actor=instance.user,
                    verb=f"comentó en tu {instance.entity_type if hasattr(instance, 'entity_type') else 'publicación'}",
                    target_content_object=target
                )

@receiver(post_save, sender=CommentReaction)
def notify_comment_reaction(sender, instance, created, **kwargs):
    if created and instance.comment.user != instance.user:
        Notification.objects.create(
            recipient=instance.comment.user,
            actor=instance.user,
            verb=f"reaccionó a tu comentario",
            target_content_object=instance.comment
        )