from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from . import views
from marketplace import views as MarketPlaceViews

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("", include("accounts.urls")),
    path("marketplace/", include("marketplace.urls")),
    path("cart/", MarketPlaceViews.cart, name="cart"),
    path("search/", MarketPlaceViews.search, name="search"),
    path("checkout/", MarketPlaceViews.checkout, name="checkout"),
    path("orders/", include("orders.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
