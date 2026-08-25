from django.db.models import Count,Q
from comunicaciones.models import Comunicacion
def datos(institucion):
 qs=Comunicacion.objects.filter(institucion=institucion).annotate(destinatarios=Count("notificaciones"),leidas=Count("notificaciones",filter=Q(notificaciones__leida=True)),pendientes=Count("notificaciones",filter=Q(notificaciones__leida=False)))
 rows=[]
 for c in qs:c.tasa=round(c.leidas*100/c.destinatarios,2) if c.destinatarios else 0;rows.append(c)
 return rows
