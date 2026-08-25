from django.core.management.base import BaseCommand
from django.utils import timezone

from suscripciones.models import Suscripcion


class Command(BaseCommand):
    help = "Marca suscripciones y pruebas vencidas. Es idempotente."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        total = Suscripcion.objects.filter(
            estado__in=(Suscripcion.Estado.ACTIVA, Suscripcion.Estado.PRUEBA), fecha_fin__lt=hoy
        ).update(estado=Suscripcion.Estado.VENCIDA)
        total += Suscripcion.objects.filter(
            estado=Suscripcion.Estado.PRUEBA, periodo_prueba_hasta__lt=hoy
        ).update(estado=Suscripcion.Estado.VENCIDA)
        self.stdout.write(self.style.SUCCESS(f"{total} suscripción(es) actualizada(s)."))
