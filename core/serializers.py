from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Organismo, Caso, Denuncia, Persona, Animal, Documento, Seguimiento, Auditoria

Usuario = get_user_model()

class UsuarioSerializer(serializers.ModelSerializer):
    organismo_nombre = serializers.CharField(source="organismo.nombre", read_only=True)
    class Meta:
        model = Usuario
        fields = ["id", "username", "first_name", "last_name", "email", "telefono", "rol", "organismo", "organismo_nombre", "is_active"]
        read_only_fields = ["id"]

class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10)
    class Meta:
        model = Usuario
        fields = ["id", "username", "password", "first_name", "last_name", "email", "telefono", "rol", "organismo", "is_active"]
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user

class OrganismoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organismo
        fields = "__all__"

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = "__all__"

class AnimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Animal
        fields = "__all__"

class DenunciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Denuncia
        fields = "__all__"
        read_only_fields = ["estado", "revisada_por", "revisada_en", "creado_por", "organismo", "caso"]

class DenunciaPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Denuncia
        fields = ["fuente", "nombre_denunciante", "contacto_denunciante", "email_denunciante", "descripcion_original", "datos_originales"]
        extra_kwargs = {
            "nombre_denunciante": {"required": True},
            "descripcion_original": {"required": True},
        }
    def validate_datos_originales(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Debe ser un objeto JSON.")
        return value
    def create(self, validated_data):
        validated_data["fuente"] = Denuncia.Fuente.CIUDADANO
        validated_data["estado"] = Denuncia.Estado.PENDIENTE
        return Denuncia.objects.create(**validated_data)

class CasoSerializer(serializers.ModelSerializer):
    personas = PersonaSerializer(many=True, read_only=True)
    animales = AnimalSerializer(many=True, read_only=True)
    cantidad_denuncias = serializers.IntegerField(source="denuncias.count", read_only=True)
    class Meta:
        model = Caso
        fields = "__all__"
        read_only_fields = ["codigo", "creado_por", "organismo", "creado_en", "actualizado_en"]

class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = "__all__"
        read_only_fields = ["cargado_por", "cargado_en"]

class SeguimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seguimiento
        fields = "__all__"
        read_only_fields = ["usuario", "fecha", "estado_anterior"]

class AuditoriaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source="usuario.username", read_only=True)
    class Meta:
        model = Auditoria
        fields = "__all__"
