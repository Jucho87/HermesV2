from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Sum, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Categoria,
    Marca,
    UnidadMedida,
    Producto,
    ProductoDetalle,
    ListaCompra,
    TransaccionDetalle,
)
from .serializers import (
    CategoriaSerializer,
    MarcaSerializer,
    UnidadMedidaSerializer,
    ProductoSerializer,
    ProductoDetalleSerializer,
    ListaCompraSerializer,
    RegistroTransaccionSerializer,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar categorías.
    """

    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class MarcaViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar marcas.
    """

    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer


class UnidadMedidaViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar unidades de medida.
    """

    queryset = UnidadMedida.objects.all()
    serializer_class = UnidadMedidaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar productos genéricos.
    """

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer


class ProductoDetalleViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar presentaciones de productos.
    Permite búsqueda por nombre y filtro por categoría y marca.
    """

    queryset = ProductoDetalle.objects.select_related(
        "producto__categoria", "marca"
    ).all()
    serializer_class = ProductoDetalleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["producto__categoria", "marca"]
    search_fields = ["producto__nombre", "marca__nombre", "presentacion"]


class ListaCompraViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar listas de compra.
    """

    queryset = ListaCompra.objects.prefetch_related("items").all()
    serializer_class = ListaCompraSerializer

    @action(detail=True, methods=["post"], url_path="registrar-compra")
    def registrar_compra(self, request, pk=None):
        lista = self.get_object()
        serializer = RegistroTransaccionSerializer(data=request.data)

        if serializer.is_valid():
            items_data = serializer.validated_data["items"]

            try:
                with transaction.atomic():
                    total_real = 0
                    for item_data in items_data:
                        detalle = TransaccionDetalle.objects.create(
                            lista_compra=lista,
                            item_lista_id=item_data.get("item_lista_id"),
                            producto_detalle_id=item_data["producto_detalle_id"],
                            cantidad_real=item_data["cantidad_real"],
                            precio_unitario_real=item_data["precio_unitario_real"],
                        )
                        total_real += detalle.subtotal_real

                    lista.total_real = total_real
                    lista.fecha_ejecucion = timezone.now().date()
                    lista.save()

                return Response(
                    {"status": "compra registrada exitosamente"},
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="reporte-comparativo")
    def reporte_comparativo(self, request, pk=None):
        lista = self.get_object()

        if not lista.fecha_ejecucion:
            return Response(
                {
                    "error": "El reporte solo puede generarse para listas de compra ejecutadas."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_estimado = lista.total_estimado
        total_real = lista.total_real
        diferencia_absoluta = total_real - total_estimado
        diferencia_porcentual = (
            (diferencia_absoluta / total_estimado * 100) if total_estimado > 0 else 0
        )

        resumen = {
            "total_estimado": total_estimado,
            "total_real": total_real,
            "diferencia_absoluta": diferencia_absoluta,
            "diferencia_porcentual": f"{diferencia_porcentual:.2f}%",
        }

        items_planeados = lista.items.all()
        transacciones = lista.transacciones.all()

        transacciones_mapeadas = {
            t.item_lista_id: t for t in transacciones if t.item_lista_id
        }

        detalle_items = []
        for item_planeado in items_planeados:
            detalle = {
                "producto": str(item_planeado.producto_detalle),
                "planeado": {
                    "cantidad": item_planeado.cantidad_planeada,
                    "precio_unitario": item_planeado.precio_estimado_unitario,
                    "subtotal": item_planeado.subtotal_estimado,
                },
                "real": None,
            }

            transaccion_real = transacciones_mapeadas.get(item_planeado.id)
            if transaccion_real:
                detalle["real"] = {
                    "cantidad": transaccion_real.cantidad_real,
                    "precio_unitario": transaccion_real.precio_unitario_real,
                    "subtotal": transaccion_real.subtotal_real,
                }

            detalle_items.append(detalle)

        items_no_planeados = []
        for transaccion in transacciones:
            if not transaccion.item_lista_id:
                items_no_planeados.append(
                    {
                        "producto": str(transaccion.producto_detalle),
                        "cantidad_real": transaccion.cantidad_real,
                        "precio_unitario_real": transaccion.precio_unitario_real,
                        "subtotal_real": transaccion.subtotal_real,
                    }
                )

        reporte = {
            "lista_nombre": lista.nombre,
            "fecha_planeada": lista.fecha_planeada,
            "fecha_ejecucion": lista.fecha_ejecucion,
            "resumen": resumen,
            "detalle_items": detalle_items,
            "items_no_planeados": items_no_planeados,
        }

        return Response(reporte)


class ReportesAPIView(APIView):
    """
    Vista para reportes analíticos.
    """

    def _get_gasto_agrupado(self, group_by_field, group_by_name):
        """
        Método auxiliar para obtener el gasto agrupado por un campo específico.
        """
        queryset = (
            TransaccionDetalle.objects.values(group_by_field)
            .annotate(total_gastado=Sum(F("cantidad_real") * F("precio_unitario_real")))
            .values("total_gastado", nombre=F(group_by_field))
        )

        return Response(list(queryset))

    def get(self, request, *args, **kwargs):
        reporte_tipo = request.query_params.get("reporte")

        if reporte_tipo == "gasto_por_categoria":
            return self._get_gasto_agrupado(
                "producto_detalle__producto__categoria__nombre", "categoria"
            )
        elif reporte_tipo == "gasto_por_marca":
            return self._get_gasto_agrupado("producto_detalle__marca__nombre", "marca")

        return Response(
            {"error": "Tipo de reporte no especificado o inválido."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class TendenciaPreciosAPIView(APIView):
    """
    Vista para obtener la tendencia histórica de precios de un producto.
    """

    def get(self, request, producto_detalle_id, *args, **kwargs):
        queryset = (
            TransaccionDetalle.objects.filter(producto_detalle_id=producto_detalle_id)
            .order_by("lista_compra__fecha_ejecucion")
            .values("lista_compra__fecha_ejecucion", "precio_unitario_real")
        )

        return Response(list(queryset))
