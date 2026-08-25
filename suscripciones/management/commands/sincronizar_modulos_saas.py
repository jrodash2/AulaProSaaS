from django.core.management.base import BaseCommand

from suscripciones.catalogo import MODULOS_OFICIALES
from suscripciones.models import ModuloSaaS


class Command(BaseCommand):
    help = "Crea o actualiza el catálogo oficial de módulos SaaS sin borrar módulos personalizados."

    def add_arguments(self, parser):
        parser.add_argument("--reactivar", action="store_true", help="Reactiva módulos oficiales desactivados de forma explícita.")

    def handle(self, *args, **options):
        creados = existentes = actualizados = 0
        for codigo, nombre, orden, descripcion, icono in MODULOS_OFICIALES:
            modulo, creado = ModuloSaaS.objects.get_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "orden": orden, "descripcion": descripcion, "icono": icono, "activo": True},
            )
            if creado:
                creados += 1
                continue
            existentes += 1
            cambios = {"nombre": nombre, "orden": orden, "descripcion": descripcion, "icono": icono}
            if options["reactivar"]:
                cambios["activo"] = True
            diferentes = [campo for campo, valor in cambios.items() if getattr(modulo, campo) != valor]
            if diferentes:
                for campo in diferentes: setattr(modulo, campo, cambios[campo])
                modulo.save(update_fields=(*diferentes,))
                actualizados += 1
        self.stdout.write(self.style.SUCCESS(f"{len(MODULOS_OFICIALES)} módulos revisados · {creados} creados · {existentes} existentes · {actualizados} actualizados"))
