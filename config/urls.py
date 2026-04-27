from django.contrib import admin
from django.urls import path, include

# Ya no necesitamos auth_views ni CustomLoginForm aquí porque el login
# ahora lo maneja tu CustomLoginView dentro de users/views.py

# NUEVAS IMPORTACIONES PARA MOSTRAR IMÁGENES
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. PRIMERO incluimos tus URLs personalizadas (Aquí vive tu login con 2FA)
    path('cuentas/', include('users.urls')), 

    # 2. DESPUÉS las de Django (Atrapará el logout, recuperar contraseña, etc.)
    path('cuentas/', include('django.contrib.auth.urls')), 

    # 3. Aquí incluimos el archivo de la app music
    path('', include('music.urls')),
]

# Le decimos a Django que permita mostrar las imágenes en fase de desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)