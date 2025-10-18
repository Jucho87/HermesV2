from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    abreviatura = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.nombre} ({self.abreviatura})"


class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    unidad_medida = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre


class ProductoDetalle(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT)
    presentacion = models.CharField(max_length=200)  # E.g., "1L", "Paquete 6 unidades"

    def __str__(self):
        return f"{self.producto.nombre} {self.marca.nombre} - {self.presentacion}"


class ListaCompra(models.Model):
    nombre = models.CharField(max_length=150)
    fecha_planeada = models.DateField()
    fecha_ejecucion = models.DateField(null=True, blank=True)
    total_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_real = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.nombre} ({self.fecha_planeada})"


class ItemLista(models.Model):
    lista_compra = models.ForeignKey(
        ListaCompra, related_name="items", on_delete=models.CASCADE
    )
    producto_detalle = models.ForeignKey(ProductoDetalle, on_delete=models.PROTECT)
    cantidad_planeada = models.PositiveIntegerField()
    precio_estimado_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal_estimado(self):
        return self.cantidad_planeada * self.precio_estimado_unitario

    def __str__(self):
        return f"{self.cantidad_planeada} x {self.producto_detalle.producto.nombre} ({self.precio_estimado_unitario})"


class TransaccionDetalle(models.Model):
    item_lista = models.OneToOneField(
        ItemLista, on_delete=models.CASCADE, null=True, blank=True
    )
    producto_detalle = models.ForeignKey(ProductoDetalle, on_delete=models.PROTECT)
    cantidad_real = models.PositiveIntegerField()
    precio_unitario_real = models.DecimalField(max_digits=10, decimal_places=2)
    lista_compra = models.ForeignKey(
        ListaCompra, related_name="transacciones", on_delete=models.CASCADE
    )

    @property
    def subtotal_real(self):
        return self.cantidad_real * self.precio_unitario_real

    def __str__(self):
        return (
            f"Compra de {self.cantidad_real} x {self.producto_detalle.producto.nombre}"
        )
