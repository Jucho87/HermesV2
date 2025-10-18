from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoriaViewSet,
    MarcaViewSet,
    UnidadMedidaViewSet,
    ProductoViewSet,
    ProductoDetalleViewSet,
    ListaCompraViewSet,
    ReportesAPIView,
    TendenciaPreciosAPIView,
)

# Creamos un router y registramos nuestros viewsets con él.
router = DefaultRouter()
router.register(r"categorias", CategoriaViewSet)
router.register(r"marcas", MarcaViewSet)
router.register(r"unidades-medida", UnidadMedidaViewSet)
router.register(r"productos", ProductoViewSet)
router.register(r"productos-detalle", ProductoDetalleViewSet)
router.register(r"listas-compra", ListaCompraViewSet)

# Las URLs del API son ahora determinadas automáticamente por el router.
urlpatterns = [
    path("", include(router.urls)),
    path("reportes/", ReportesAPIView.as_view(), name="reportes"),
    path(
        "reportes/tendencia-precios/<int:producto_detalle_id>/",
        TendenciaPreciosAPIView.as_view(),
        name="tendencia-precios",
    ),
]
