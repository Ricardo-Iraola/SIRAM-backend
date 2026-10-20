import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Organismo(models.Model):
    nombre = models.CharField(max_length=160, unique=True)
    sigla = models.CharField(max_length=30, blank=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.sigla or self.nombre


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador del sistema"
        AGENTE = "AGENTE", "Agente interno"
        ANALISTA = "ANALISTA", "Analista / Comité"

    rol = models.CharField(max_length=12, choices=Rol.choices, default=Rol.AGENTE)
    organismo = models.ForeignKey(Organismo, null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios")
    telefono = models.CharField(max_length=30, blank=True)

    @property
    def es_admin_siram(self):
        return self.is_superuser or self.rol == self.Rol.ADMIN


class Caso(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        EN_REVISION = "EN_REVISION", "En revisión"
        INCOMPLETO = "INCOMPLETO", "Incompleto"
        EN_SEGUIMIENTO = "EN_SEGUIMIENTO", "En seguimiento"
        CERRADO = "CERRADO", "Cerrado"

    class TipoEvento(models.TextChoices):
        ATAQUE = "ATAQUE", "Ataque"
        MORDEDURA = "MORDEDURA", "Mordedura"
        ARANAZO = "ARANAZO", "Arañazo"
        LESION = "LESION", "Otra lesión compatible"

    codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    fecha_evento = models.DateTimeField(db_index=True)
    tipo_evento = models.CharField(max_length=20, choices=TipoEvento.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTO, db_index=True)
    descripcion = models.TextField(blank=True)
    via_publica = models.BooleanField(default=False)
    direccion = models.CharField(max_length=255, blank=True)
    barrio = models.CharField(max_length=100, blank=True)
    localidad = models.CharField(max_length=100, default="Ushuaia")
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    contexto = models.CharField(max_length=120, blank=True)
    creado_por = models.ForeignKey("core.Usuario", null=True, on_delete=models.SET_NULL, related_name="casos_creados")
    organismo = models.ForeignKey(Organismo, null=True, blank=True, on_delete=models.PROTECT, related_name="casos")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_evento"]
        indexes = [models.Index(fields=["fecha_evento", "estado"]), models.Index(fields=["barrio", "localidad"])]

    def __str__(self):
        return f"Caso {str(self.codigo)[:8]}"


class Persona(models.Model):
    class RolPersona(models.TextChoices):
        VICTIMA = "VICTIMA", "Víctima"
        DENUNCIANTE = "DENUNCIANTE", "Denunciante"
        RESPONSABLE = "RESPONSABLE", "Responsable del animal"

    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name="personas")
    rol = models.CharField(max_length=20, choices=RolPersona.choices)
    nombre = models.CharField(max_length=120)
    apellido = models.CharField(max_length=120, blank=True)
    dni = models.CharField(max_length=20, blank=True, db_index=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    es_menor = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} {self.apellido}".strip()


class Animal(models.Model):
    class Especie(models.TextChoices):
        PERRO = "PERRO", "Perro"
        GATO = "GATO", "Gato"

    class Tenencia(models.TextChoices):
        DOMICILIADO = "DOMICILIADO", "Domiciliado"
        COMUNITARIO = "COMUNITARIO", "Comunitario"
        SUELTO = "SUELTO", "Suelto"
        DESCONOCIDO = "DESCONOCIDO", "Desconocido"

    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name="animales")
    especie = models.CharField(max_length=10, choices=Especie.choices, default=Especie.PERRO)
    nombre = models.CharField(max_length=100, blank=True)
    raza = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=80, blank=True)
    sexo = models.CharField(max_length=20, blank=True)
    tenencia = models.CharField(max_length=20, choices=Tenencia.choices, default=Tenencia.DESCONOCIDO)
    tiene_identificacion = models.BooleanField(default=False)
    identificacion = models.CharField(max_length=100, blank=True)
    vacunacion_antirrabica = models.CharField(max_length=30, blank=True)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_especie_display()} - {self.nombre or 'sin nombre'}"


class Denuncia(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de revisión"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    class Fuente(models.TextChoices):
        CIUDADANO = "CIUDADANO", "Canal ciudadano"
        MUNICIPIO = "MUNICIPIO", "Municipio"
        SALUD = "SALUD", "Salud"
        IMPORTACION = "IMPORTACION", "Importación"
        OTRO = "OTRO", "Otro organismo"

    caso = models.ForeignKey(Caso, null=True, blank=True, on_delete=models.SET_NULL, related_name="denuncias")
    fuente = models.CharField(max_length=20, choices=Fuente.choices, default=Fuente.CIUDADANO)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    fecha_recepcion = models.DateTimeField(default=timezone.now)
    nombre_denunciante = models.CharField(max_length=120, blank=True)
    contacto_denunciante = models.CharField(max_length=120, blank=True)
    email_denunciante = models.EmailField(blank=True)
    descripcion_original = models.TextField(blank=True)
    datos_originales = models.JSONField(default=dict, blank=True)
    observacion_revision = models.TextField(blank=True)
    revisada_por = models.ForeignKey("core.Usuario", null=True, blank=True, on_delete=models.SET_NULL, related_name="denuncias_revisadas")
    revisada_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey("core.Usuario", null=True, blank=True, on_delete=models.SET_NULL, related_name="denuncias_creadas")
    organismo = models.ForeignKey(Organismo, null=True, blank=True, on_delete=models.PROTECT, related_name="denuncias")

    class Meta:
        ordering = ["-fecha_recepcion"]

    def __str__(self):
        return f"Denuncia #{self.pk} ({self.estado})"


class Documento(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        VALIDADO = "VALIDADO", "Validado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField(max_length=80)
    archivo = models.FileField(upload_to="documentos/%Y/%m/")
    descripcion = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    cargado_por = models.ForeignKey("core.Usuario", null=True, on_delete=models.SET_NULL)
    cargado_en = models.DateTimeField(auto_now_add=True)


class Seguimiento(models.Model):
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name="seguimientos")
    estado_anterior = models.CharField(max_length=20, blank=True)
    estado_nuevo = models.CharField(max_length=20, choices=Caso.Estado.choices)
    accion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey("core.Usuario", null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-fecha"]


class Auditoria(models.Model):
    usuario = models.ForeignKey("core.Usuario", null=True, on_delete=models.SET_NULL)
    accion = models.CharField(max_length=80)
    entidad = models.CharField(max_length=80)
    entidad_id = models.CharField(max_length=80, blank=True)
    detalle = models.JSONField(default=dict, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
