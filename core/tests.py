from django.test import TestCase
from rest_framework.test import APIClient
from .models import Denuncia

class DenunciaPublicaTests(TestCase):
    def test_denuncia_publica_queda_pendiente(self):
        client = APIClient()
        response = client.post("/api/denuncias/publica/", {
            "fuente": "CIUDADANO",
            "nombre_denunciante": "Persona de prueba",
            "descripcion_original": "Incidente de prueba",
            "datos_originales": {"localidad": "Ushuaia"}
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Denuncia.objects.count(), 1)
        self.assertEqual(Denuncia.objects.first().estado, Denuncia.Estado.PENDIENTE)
