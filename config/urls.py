from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from cuentas.forms import AulaProAuthenticationForm
from core.health import health,health_db
urlpatterns = [
    path("health/", health, name="health"),
    path("health/db/", health_db, name="health_db"),
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=AulaProAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("core.urls")),
    path("institucion/", include("instituciones.urls")),
    path("catalogos/", include("catalogos.urls")),
    path("academico/", include("academico.urls")),
    path("alumnos/", include("alumnos.urls")),
    path("docentes/", include("docentes.urls")),
    path("asistencia/", include("asistencia.urls")),
    path("calificaciones/", include("calificaciones.urls")),
    path("tareas/", include("tareas.urls")),
    path("finanzas/", include("finanzas.urls")),
    path("portal/", include("portal.urls")),
    path("comunicacion/", include("comunicaciones.urls")),
    path("reportes/", include("reportes.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
