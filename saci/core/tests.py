from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import (
    Categoria,
    Marca,
    UnidadMedida,
    Producto,
    ProductoDetalle,
    ListaCompra,
    TransaccionDetalle,
)


class SaciApiTests(APITestCase):
    def setUp(self):
        """
        Configura los datos iniciales para las pruebas.
        """
        # Creación de Maestros
        self.categoria_lacteos = Categoria.objects.create(nombre="Lácteos")
        self.marca_alpina = Marca.objects.create(nombre="Alpina")
        self.unidad_litro = UnidadMedida.objects.create(nombre="Litro", abreviatura="L")

        self.producto_leche = Producto.objects.create(
            nombre="Leche Entera",
            categoria=self.categoria_lacteos,
            unidad_medida=self.unidad_litro,
        )

        self.producto_detalle_leche = ProductoDetalle.objects.create(
            producto=self.producto_leche,
            marca=self.marca_alpina,
            presentacion="Bolsa 1L",
        )

        # Producto adicional para la prueba de ítems no planeados
        self.categoria_panaderia = Categoria.objects.create(nombre="Panadería")
        self.marca_bimbo = Marca.objects.create(nombre="Bimbo")
        self.unidad_paquete = UnidadMedida.objects.create(
            nombre="Paquete", abreviatura="paq"
        )
        self.producto_pan = Producto.objects.create(
            nombre="Pan Tajado",
            categoria=self.categoria_panaderia,
            unidad_medida=self.unidad_paquete,
        )
        self.producto_detalle_pan = ProductoDetalle.objects.create(
            producto=self.producto_pan,
            marca=self.marca_bimbo,
            presentacion="Paquete 500g",
        )

    def test_flujo_completo_compra_y_reportes(self):
        """
        Prueba el flujo completo: crear lista, registrar compra y generar reportes.
        """
        # 1. Crear Lista de Compra
        url_crear_lista = reverse("listacompra-list")
        data_crear_lista = {
            "nombre": "Compras de la semana",
            "fecha_planeada": "2024-01-15",
            "items": [
                {
                    "producto_detalle": self.producto_detalle_leche.id,
                    "cantidad_planeada": 2,
                    "precio_estimado_unitario": "2800.00",
                }
            ],
        }
        response = self.client.post(url_crear_lista, data_crear_lista, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ListaCompra.objects.count(), 1)

        lista_creada = ListaCompra.objects.first()
        self.assertEqual(lista_creada.total_estimado, 5600.00)
        self.assertEqual(lista_creada.items.count(), 1)
        item_creado = lista_creada.items.first()

        # 2. Registrar Transacción
        url_registrar_compra = reverse(
            "listacompra-registrar-compra", kwargs={"pk": lista_creada.id}
        )
        data_registrar_compra = {
            "items": [
                {
                    "item_lista_id": item_creado.id,
                    "producto_detalle_id": self.producto_detalle_leche.id,
                    "cantidad_real": 2,
                    "precio_unitario_real": "2900.00",  # Precio subió
                },
                {
                    "item_lista_id": None,  # Ítem no planeado
                    "producto_detalle_id": self.producto_detalle_pan.id,
                    "cantidad_real": 1,
                    "precio_unitario_real": "4500.00",
                },
            ]
        }
        response = self.client.post(
            url_registrar_compra, data_registrar_compra, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        lista_actualizada = ListaCompra.objects.get(id=lista_creada.id)
        self.assertIsNotNone(lista_actualizada.fecha_ejecucion)
        # Total real: (2 * 2900) + (1 * 4500) = 5800 + 4500 = 10300
        self.assertEqual(lista_actualizada.total_real, 10300.00)
        self.assertEqual(TransaccionDetalle.objects.count(), 2)

        # 3. Generar Reporte Comparativo
        url_reporte_comp = reverse(
            "listacompra-reporte-comparativo", kwargs={"pk": lista_creada.id}
        )
        response = self.client.get(url_reporte_comp)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resumen"]["total_estimado"], 5600.00)
        self.assertEqual(response.data["resumen"]["total_real"], 10300.00)
        self.assertEqual(len(response.data["items_no_planeados"]), 1)

        # 4. Generar Reporte de Gasto por Categoría
        url_reporte_gasto = reverse("reportes") + "?reporte=gasto_por_categoria"
        response = self.client.get(url_reporte_gasto)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Lácteos y Panadería
        gasto_lacteos = next(
            item for item in response.data if item["nombre"] == "Lácteos"
        )
        self.assertEqual(gasto_lacteos["total_gastado"], 5800.00)

        # 5. Generar Reporte de Tendencia de Precios
        url_reporte_tendencia = reverse(
            "tendencia-precios",
            kwargs={"producto_detalle_id": self.producto_detalle_leche.id},
        )
        response = self.client.get(url_reporte_tendencia)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["precio_unitario_real"], Decimal("2900.00"))
