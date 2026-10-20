from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Organismo, Caso, Denuncia, Persona, Animal, Documento, Seguimiento, Auditoria

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("SIRAM", {"fields": ("rol", "organismo", "telefono")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("SIRAM", {"fields": ("rol", "organismo", "telefono")}),)
    list_display = ("username", "email", "rol", "organismo", "is_active")
    list_filter = ("rol", "organismo", "is_active")

@admin.register(Caso)
class CasoAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo", "fecha_evento", "tipo_evento", "estado", "barrio", "organismo")
    list_filter = ("estado", "tipo_evento", "organismo", "localidad")
    search_fields = ("direccion", "barrio", "descripcion")

@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ("id", "fuente", "estado", "fecha_recepcion", "nombre_denunciante", "caso")
    list_filter = ("estado", "fuente")
    search_fields = ("nombre_denunciante", "descripcion_original")

for model in (Organismo, Persona, Animal, Documento, Seguimiento, Auditoria):
    admin.site.register(model)
