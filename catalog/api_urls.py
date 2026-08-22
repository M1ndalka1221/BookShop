from rest_framework.routers import DefaultRouter
from .api_views import CategoryViewSet, BookViewSet, OrderViewSet, CartViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('books', BookViewSet, basename='book')
router.register('orders', OrderViewSet, basename='order')
router.register('cart', CartViewSet, basename='cart')

urlpatterns = router.urls
