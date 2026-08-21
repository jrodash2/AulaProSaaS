from django.contrib.auth import get_user_model
from django.db import transaction
from instituciones.models import UsuarioInstitucion

@transaction.atomic
def crear_acceso_docente(docente,datos):
    usuario=get_user_model().objects.create_user(username=datos["username"],email=datos["email"],password=datos["password"],first_name=docente.primer_nombre,last_name=docente.primer_apellido)
    UsuarioInstitucion.objects.create(usuario=usuario,institucion=docente.institucion,rol=UsuarioInstitucion.Rol.DOCENTE)
    docente.usuario=usuario; docente.save(update_fields=("usuario","fecha_actualizacion")); return usuario

@transaction.atomic
def cambiar_acceso_docente(docente,activo):
    asignacion=UsuarioInstitucion.objects.select_for_update().get(usuario=docente.usuario,institucion=docente.institucion,rol=UsuarioInstitucion.Rol.DOCENTE)
    asignacion.activo=activo; asignacion.save(update_fields=("activo",)); return asignacion
