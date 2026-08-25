from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from instituciones.models import Institucion
from suscripciones.models import Suscripcion
from suscripciones.services import crear_catalogo_inicial


class Command(BaseCommand):
    help = "Asigna un plan a instituciones históricas sin suscripción."

    def add_arguments(self, parser):
        parser.add_argument("--plan", default="INICIO")
        parser.add_argument("--trial-dias", type=int, default=30)

    def handle(self, *args, **options):
        planes = crear_catalogo_inicial()
        codigo = options["plan"].upper()
        if codigo not in planes: raise CommandError(f"Plan desconocido: {codigo}")
        dias = options["trial_dias"]
        if dias < 0: raise CommandError("--trial-dias no puede ser negativo.")
        hoy = timezone.localdate(); total = 0
        for institucion in Institucion.objects.exclude(suscripciones__estado__in=("PRUEBA", "ACTIVA", "SUSPENDIDA")):
            fin = hoy + timedelta(days=dias or 30)
            Suscripcion.objects.create(institucion=institucion, plan=planes[codigo], estado="PRUEBA" if dias else "ACTIVA", modalidad="MENSUAL", fecha_inicio=hoy, fecha_fin=fin, periodo_prueba_hasta=fin if dias else None)
            total += 1
        self.stdout.write(self.style.SUCCESS(f"{total} institución(es) asignada(s)."))
