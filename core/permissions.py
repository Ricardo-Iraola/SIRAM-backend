from rest_framework.permissions import BasePermission, SAFE_METHODS

class EsAdminSiram(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "rol", None) == "ADMIN"))

class PuedeGestionarCasos(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "rol", None) in ("ADMIN", "AGENTE", "ANALISTA"))

class SoloLecturaOAgente(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_superuser or getattr(user, "rol", None) in ("ADMIN", "AGENTE")
