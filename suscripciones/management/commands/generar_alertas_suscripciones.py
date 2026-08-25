from django.core.management.base import BaseCommand
from django.utils import timezone

from comunicaciones.services import crear_notificacion
from instituciones.models import UsuarioInstitucion
from suscripciones.models import Suscripcion


class Command(BaseCommand):
    help = "Genera alertas internas de renovación a 30, 15, 7 y 1 días."

    def handle(self, *args, **options):
        hoy = timezone.localdate(); total = 0
        for suscripcion in Suscripcion.objects.filter(estado__in=("ACTIVA", "PRUEBA")).select_related("institucion", "plan"):
            dias = (suscripcion.fecha_fin - hoy).days
            if dias not in (30, 15, 7, 1): continue
            for asignacion in UsuarioInstitucion.objects.filter(institucion=suscripcion.institucion, rol="PROPIETARIO", activo=True).select_related("usuario"):
                from comunicaciones.models import Notificacion
                origen = f"suscripcion:{suscripcion.pk}:vence:{dias}"
                existe = Notificacion.objects.filter(institucion=suscripcion.institucion, usuario=asignacion.usuario, tipo_origen="SUSCRIPCION", origen_id=origen).exists()
                crear_notificacion(institucion=suscripcion.institucion, usuario=asignacion.usuario, titulo=f"Tu suscripción de AulaPro vence en {dias} día{'s' if dias != 1 else ''}", mensaje=f"Plan {suscripcion.plan.nombre} · vence {suscripcion.fecha_fin:%d/%m/%Y}", tipo="SUSCRIPCION", url="/institucion/suscripcion/", origen_id=origen)
                total += int(not existe)
        self.stdout.write(self.style.SUCCESS(f"{total} alerta(s) creada(s)."))
