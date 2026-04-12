from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, FriendRequest, MusicianVerificationRequest

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Roles en Riff', {'fields': ('is_listener', 'is_musician')}),
        ('Privacidad y Red', {'fields': ('is_private', 'friends')}),
    )
    list_display = ('username', 'email', 'is_listener', 'is_musician', 'is_private')
    # Permite buscar usuarios fácilmente en el admin
    filter_horizontal = ('friends',)

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'is_active', 'timestamp')
    list_filter = ('is_active',)

# --- EL NUEVO MÓDULO DE VERIFICACIÓN ---
@admin.register(MusicianVerificationRequest)
class MusicianVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at')
    list_filter = ('status',)