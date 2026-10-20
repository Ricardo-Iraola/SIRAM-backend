from .models import Auditoria, Caso, Denuncia

def registrar_auditoria(request, accion, entidad, entidad_id="", detalle=None):
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    Auditoria.objects.create(
        usuario=user, accion=accion, entidad=entidad, entidad_id=str(entidad_id),
        detalle=detalle or {}, ip=ip or None
    )

def posibles_duplicados(caso):
    """Devuelve candidatos para revisión humana; nunca consolida automáticamente."""
    qs = Caso.objects.exclude(pk=caso.pk).filter(fecha_evento__date=caso.fecha_evento.date())
    if caso.barrio:
        qs = qs.filter(barrio__iexact=caso.barrio)
    if caso.direccion:
        qs = qs.filter(direccion__iexact=caso.direccion)
    return qs[:20]

def registrar_estado_denuncia(denuncia, estado, usuario, observacion=""):
    denuncia.estado = estado
    denuncia.revisada_por = usuario
    from django.utils import timezone
    denuncia.revisada_en = timezone.now()
    denuncia.observacion_revision = observacion
    denuncia.save(update_fields=["estado", "revisada_por", "revisada_en", "observacion_revision"])
