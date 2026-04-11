from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from users.forms import CustomLoginForm

# NUEVAS IMPORTACIONES PARA MOSTRAR IMÁGENES
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('cuentas/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        authentication_form=CustomLoginForm
    ), name='login'),
    
    path('cuentas/', include('django.contrib.auth.urls')), 
    path('cuentas/', include('users.urls')), 

    # CORRECTO: Aquí solo incluimos el archivo de la app music
    path('', include('music.urls')),
]

# NUEVO: Le decimos a Django que permita mostrar las imágenes en fase de desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)