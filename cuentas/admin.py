from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "activo", "is_staff", "is_superuser")
    list_filter = ("activo", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (("AulaPro", {"fields": ("activo",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("AulaPro", {"fields": ("email", "first_name", "last_name", "activo")}),)
