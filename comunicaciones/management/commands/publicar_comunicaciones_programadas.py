from django.core.management.base import BaseCommand
from django.utils import timezone
from comunicaciones.models import Comunicacion
from comunicaciones.services import sincronizar_notificaciones
class Command(BaseCommand):
    help="Publica comunicaciones programadas cuya fecha ya llegó."
    def handle(self,*args,**options):
        qs=Comunicacion.objects.filter(estado="PROGRAMADA",fecha_publicacion__lte=timezone.now())
        total=0
        for com in qs.iterator():com.estado="PUBLICADA";com.save(update_fields=("estado","fecha_actualizacion"));sincronizar_notificaciones(com);total+=1
        self.stdout.write(self.style.SUCCESS(f"{total} comunicación(es) publicada(s)."))
