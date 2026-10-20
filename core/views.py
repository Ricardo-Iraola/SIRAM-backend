from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Organismo, Caso, Denuncia, Persona, Animal, Documento, Seguimiento, Auditoria
from .serializers import (
    UsuarioSerializer, UsuarioCreateSerializer, OrganismoSerializer, CasoSerializer,
    DenunciaSerializer, DenunciaPublicaSerializer, PersonaSerializer, AnimalSerializer,
    DocumentoSerializer, SeguimientoSerializer, AuditoriaSerializer
)
from .permissions import EsAdminSiram, PuedeGestionarCasos, SoloLecturaOAgente
from .services import registrar_auditoria, posibles_duplicados, registrar_estado_denuncia

Usuario = get_user_model()

class BaseAuditViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        obj = serializer.save()
        registrar_auditoria(self.request, "CREAR", obj.__class__.__name__, obj.pk)
    def perform_update(self, serializer):
        obj = serializer.save()
        registrar_auditoria(self.request, "MODIFICAR", obj.__class__.__name__, obj.pk)
    def perform_destroy(self, instance):
        registrar_auditoria(self.request, "ELIMINAR", instance.__class__.__name__, instance.pk)
        instance.delete()

class UsuarioViewSet(BaseAuditViewSet):
    queryset = Usuario.objects.select_related("organismo").all()
    filterset_fields = ["rol", "organismo", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return [EsAdminSiram()]

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UsuarioSerializer(request.user).data)

class OrganismoViewSet(BaseAuditViewSet):
    queryset = Organismo.objects.all()
    serializer_class = OrganismoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["activo"]
    search_fields = ["nombre", "sigla"]
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated()]
        return [EsAdminSiram()]

class CasoViewSet(BaseAuditViewSet):
    queryset = Caso.objects.select_related("creado_por", "organismo").prefetch_related("personas", "animales", "denuncias")
    serializer_class = CasoSerializer
    permission_classes = [SoloLecturaOAgente]
    filterset_fields = ["estado", "tipo_evento", "barrio", "localidad", "organismo", "via_publica"]
    search_fields = ["direccion", "barrio", "descripcion", "personas__nombre", "personas__apellido"]
    ordering_fields = ["fecha_evento", "creado_en", "estado"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not user.is_superuser and user.rol != "ADMIN" and user.organismo_id:
            # Scope to the user's organism, while allowing cases without assigned organism to be reviewed.
            qs = qs.filter(organismo__in=[user.organismo_id])
        return qs.distinct()

    def perform_create(self, serializer):
        user = self.request.user
        obj = serializer.save(creado_por=user, organismo=getattr(user, "organismo", None))
        registrar_auditoria(self.request, "CREAR", "Caso", obj.pk)

    def perform_update(self, serializer):
        anterior = serializer.instance.estado
        obj = serializer.save()
        if anterior != obj.estado:
            Seguimiento.objects.create(caso=obj, estado_anterior=anterior, estado_nuevo=obj.estado, accion="Cambio de estado", usuario=self.request.user)
        registrar_auditoria(self.request, "MODIFICAR", "Caso", obj.pk)

    @action(detail=True, methods=["get"])
    def posibles_duplicados(self, request, pk=None):
        caso = self.get_object()
        data = CasoSerializer(posibles_duplicados(caso), many=True).data
        return Response(data)

    @action(detail=True, methods=["post"])
    def consolidar_denuncia(self, request, pk=None):
        caso = self.get_object()
        denuncia_id = request.data.get("denuncia_id")
        try:
            denuncia = Denuncia.objects.get(pk=denuncia_id)
        except (Denuncia.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Denuncia no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        denuncia.caso = caso
        denuncia.estado = Denuncia.Estado.APROBADA
        denuncia.revisada_por = request.user
        denuncia.revisada_en = timezone.now()
        denuncia.save()
        registrar_auditoria(request, "VINCULAR_DENUNCIA", "Caso", caso.pk, {"denuncia_id": denuncia.pk})
        return Response({"detail": "Denuncia vinculada al caso.", "caso_id": caso.pk, "denuncia_id": denuncia.pk})

class DenunciaViewSet(BaseAuditViewSet):
    queryset = Denuncia.objects.select_related("caso", "organismo", "creado_por", "revisada_por").all()
    serializer_class = DenunciaSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["estado", "fuente", "organismo", "caso"]
    search_fields = ["nombre_denunciante", "contacto_denunciante", "descripcion_original"]
    ordering_fields = ["fecha_recepcion", "estado"]

    def get_permissions(self):
        if self.action == "crear_publica":
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="publica")
    def crear_publica(self, request):
        serializer = DenunciaPublicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        denuncia = serializer.save()
        registrar_auditoria(request, "DENUNCIA_PUBLICA", "Denuncia", denuncia.pk, {"fuente": denuncia.fuente})
        return Response({"id": denuncia.pk, "estado": denuncia.estado, "mensaje": "La denuncia fue recibida y queda pendiente de revisión."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        denuncia = self.get_object()
        if not (request.user.is_superuser or request.user.rol in ("ADMIN", "AGENTE")):
            return Response({"detail": "No tiene permisos para aprobar denuncias."}, status=status.HTTP_403_FORBIDDEN)
        registrar_estado_denuncia(denuncia, Denuncia.Estado.APROBADA, request.user, request.data.get("observacion", ""))
        registrar_auditoria(request, "APROBAR", "Denuncia", denuncia.pk)
        return Response(self.get_serializer(denuncia).data)

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        denuncia = self.get_object()
        if not (request.user.is_superuser or request.user.rol in ("ADMIN", "AGENTE")):
            return Response({"detail": "No tiene permisos para rechazar denuncias."}, status=status.HTTP_403_FORBIDDEN)
        registrar_estado_denuncia(denuncia, Denuncia.Estado.RECHAZADA, request.user, request.data.get("observacion", ""))
        registrar_auditoria(request, "RECHAZAR", "Denuncia", denuncia.pk)
        return Response(self.get_serializer(denuncia).data)

class PersonaViewSet(BaseAuditViewSet):
    queryset = Persona.objects.select_related("caso").all()
    serializer_class = PersonaSerializer
    permission_classes = [SoloLecturaOAgente]
    filterset_fields = ["caso", "rol", "es_menor"]
    search_fields = ["nombre", "apellido", "dni"]

class AnimalViewSet(BaseAuditViewSet):
    queryset = Animal.objects.select_related("caso").all()
    serializer_class = AnimalSerializer
    permission_classes = [SoloLecturaOAgente]
    filterset_fields = ["caso", "especie", "tenencia", "tiene_identificacion"]
    search_fields = ["nombre", "raza", "identificacion"]

class DocumentoViewSet(BaseAuditViewSet):
    queryset = Documento.objects.select_related("caso", "cargado_por").all()
    serializer_class = DocumentoSerializer
    permission_classes = [SoloLecturaOAgente]
    filterset_fields = ["caso", "tipo", "estado"]
    def perform_create(self, serializer):
        obj = serializer.save(cargado_por=self.request.user)
        registrar_auditoria(self.request, "CARGAR_DOCUMENTO", "Documento", obj.pk)

class SeguimientoViewSet(BaseAuditViewSet):
    queryset = Seguimiento.objects.select_related("caso", "usuario").all()
    serializer_class = SeguimientoSerializer
    permission_classes = [SoloLecturaOAgente]
    filterset_fields = ["caso", "estado_nuevo", "usuario"]
    def perform_create(self, serializer):
        obj = serializer.save(usuario=self.request.user)
        registrar_auditoria(self.request, "SEGUIMIENTO", "Caso", obj.caso_id, {"seguimiento_id": obj.pk})

class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Auditoria.objects.select_related("usuario").all()
    serializer_class = AuditoriaSerializer
    permission_classes = [EsAdminSiram]
    filterset_fields = ["accion", "entidad", "usuario"]
    search_fields = ["entidad", "entidad_id", "accion"]

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Caso.objects.all()
        if not (request.user.is_superuser or request.user.rol == "ADMIN") and request.user.organismo_id:
            qs = qs.filter(organismo_id=request.user.organismo_id)
        por_estado = list(qs.values("estado").annotate(total=Count("id")).order_by("estado"))
        por_tipo = list(qs.values("tipo_evento").annotate(total=Count("id")).order_by("tipo_evento"))
        return Response({
            "total_casos": qs.count(),
            "casos_abiertos": qs.exclude(estado=Caso.Estado.CERRADO).count(),
            "denuncias_pendientes": Denuncia.objects.filter(estado=Denuncia.Estado.PENDIENTE).count(),
            "casos_por_estado": por_estado,
            "casos_por_tipo": por_tipo,
            "actualizado_en": timezone.now(),
        })
