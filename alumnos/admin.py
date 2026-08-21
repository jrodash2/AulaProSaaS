from django.contrib import admin
from .models import Alumno,AlumnoEncargado,Encargado,Familia,ImportacionAlumnos,Inscripcion
admin.site.register([Alumno,AlumnoEncargado,Encargado,Familia,ImportacionAlumnos,Inscripcion])
