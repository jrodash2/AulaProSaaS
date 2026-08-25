from django.contrib import admin
from .models import HistorialSuscripcion, ModuloSaaS, Plan, PlanModulo, SolicitudCambioPlan, Suscripcion

admin.site.register((ModuloSaaS, Plan, PlanModulo, Suscripcion, HistorialSuscripcion, SolicitudCambioPlan))
