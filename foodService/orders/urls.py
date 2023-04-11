from django.urls import path

from . import views


urlpatterns = [
    path("place-order/", views.place_order, name="place_order"),
    # stripe
    path("success/", views.payment_success, name="success"),
    path("failed/", views.payment_failed, name="failed"),
    path(
        "order_buy/<id>/",
        views.create_checkout_session_order,
        name="api_checkout_session_order",
    ),
]
