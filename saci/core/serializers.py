from rest_framework import serializers
from .models import (
    Categoria,
    Marca,
    UnidadMedida,
    Producto,
    ProductoDetalle,
    ListaCompra,
    ItemLista,
    TransaccionDetalle,
)


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = "__all__"


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = "__all__"


class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = "__all__"


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = "__all__"


class ProductoDetalleSerializer(serializers.ModelSerializer):
    # Para mostrar los nombres en lugar de los IDs en las respuestas del API
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    marca_nombre = serializers.CharField(source="marca.nombre", read_only=True)
    categoria_nombre = serializers.CharField(
        source="producto.categoria.nombre", read_only=True
    )

    class Meta:
        model = ProductoDetalle
        fields = [
            "id",
            "producto",
            "marca",
            "presentacion",
            "producto_nombre",
            "marca_nombre",
            "categoria_nombre",
        ]
        # 'producto' y 'marca' serán de solo escritura para la creación/actualización
        extra_kwargs = {
            "producto": {"write_only": True},
            "marca": {"write_only": True},
        }


class ItemListaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto_detalle.__str__', read_only=True)

    class Meta:
        model = ItemLista
        fields = [
            "id",
            "producto_detalle",
            "producto_nombre",
            "cantidad_planeada",
            "precio_estimado_unitario",
        ]


class ListaCompraSerializer(serializers.ModelSerializer):
    items = ItemListaSerializer(many=True)

    class Meta:
        model = ListaCompra
        fields = ["id", "nombre", "fecha_planeada", "total_estimado", "items"]
        read_only_fields = ["total_estimado"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        total_estimado = sum(
            item["cantidad_planeada"] * item["precio_estimado_unitario"]
            for item in items_data
        )
        validated_data["total_estimado"] = total_estimado
        lista_compra = ListaCompra.objects.create(**validated_data)
        for item_data in items_data:
            ItemLista.objects.create(lista_compra=lista_compra, **item_data)
        return lista_compra


class TransaccionDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransaccionDetalle
        fields = "__all__"


class ItemTransaccionSerializer(serializers.Serializer):
    """
    Serializador para un ítem individual dentro de una transacción.
    Puede estar o no vinculado a un ítem de la lista de planeación.
    """

    item_lista_id = serializers.IntegerField(required=False, allow_null=True)
    producto_detalle_id = serializers.IntegerField()
    cantidad_real = serializers.IntegerField()
    precio_unitario_real = serializers.DecimalField(max_digits=10, decimal_places=2)


class RegistroTransaccionSerializer(serializers.Serializer):
    """
    Serializador para el payload completo del registro de una transacción.
    """

    items = ItemTransaccionSerializer(many=True)
