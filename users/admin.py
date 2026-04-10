from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, FriendRequest

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