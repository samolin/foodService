from django.shortcuts import render, redirect, HttpResponse
import simplejson as json
from django.views.decorators.csrf import csrf_exempt
import stripe
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required

from marketplace.models import Cart
from marketplace.context_processors import get_cart_amounts
from .forms import OrderForm
from .models import Order, Payment, OrderedFood
from .utils import generate_order_number
from accounts.utils import send_notification


@login_required(login_url="login")
def place_order(request):
    cart_items = Cart.objects.filter(user=request.user).order_by("created_at")
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect("marketplace")
    subtotal = get_cart_amounts(request)["subtotal"]
    total_tax = get_cart_amounts(request)["tax"]
    grand_total = get_cart_amounts(request)["grand_total"]
    tax_data = get_cart_amounts(request)["tax_dict"]
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = Order()
            order.first_name = form.cleaned_data["first_name"]
            order.last_name = form.cleaned_data["last_name"]
            order.phone = form.cleaned_data["phone"]
            order.email = form.cleaned_data["email"]
            order.address = form.cleaned_data["address"]
            order.country = form.cleaned_data["country"]
            order.state = form.cleaned_data["state"]
            order.city = form.cleaned_data["city"]
            order.pin_code = form.cleaned_data["pin_code"]
            order.user = request.user
            order.total = grand_total
            order.tax_data = json.dumps(tax_data)
            order.total_tax = total_tax
            order.save()
            order.order_number = generate_order_number(order.id)
            order.save()
            context = {
                "order": order,
                "cart_items": cart_items,
            }
            return render(request, "orders/place_order.html", context)
        else:
            print(form.errors)
    return render(request, "orders/place_order.html")


@login_required(login_url="login")
@csrf_exempt
def create_checkout_session_order(request, id):
    main_domain = settings.MAIN_DOMAIN
    current_order = Order.objects.get(order_number=id)
    line_items_attrs = []
    line_items_attrs.append(
        {
            "price_data": {
                "currency": "usd",
                "unit_amount": int(get_cart_amounts(request)["grand_total"]) * 100,
                "product_data": {
                    "name": current_order.order_number,
                },
            },
            "quantity": 1,
        }
    )
    stripe.api_key = settings.STRIPE_SECRET_KEY
    checkout_session = stripe.checkout.Session.create(
        customer_email=request.user.email,
        payment_method_types=["card"],
        line_items=line_items_attrs,
        mode="payment",
        success_url=main_domain
        + "/orders"
        + "/success/"
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=main_domain
        + "/orders"
        + "/failed/"
        + "?session_id={CHECKOUT_SESSION_ID}",
    )
    return JsonResponse({"sessionId": checkout_session.id})


@login_required(login_url="login")
def payment_success(request):
    session_id = request.GET["session_id"]
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session_data = stripe.checkout.Session.retrieve(
        session_id,
    )
    line_items = stripe.checkout.Session.list_line_items(session_id, limit=1)
    # create new payment
    if Payment.objects.filter(transaction_id=session_data["id"]):
        return redirect("cprofile")
    else:
        payment = Payment(
            user=request.user,
            transaction_id=session_data["id"],
            payment_method=session_data["payment_method_types"][0].capitalize(),
            amount=session_data["amount_total"] / 100,
            status=session_data["payment_status"],
        )
        payment.save()
        # update order
        order = Order.objects.get(
            user=request.user, order_number=line_items.data[0]["description"]
        )
        order.payment = payment
        order.is_ordered = True
        order.save()
        # move cart items to the order
        cart_items = Cart.objects.filter(user=request.user)
        for item in cart_items:
            ordered_food = OrderedFood()
            ordered_food.order = order
            ordered_food.payment = payment
            ordered_food.user = request.user
            ordered_food.fooditem = item.fooditem
            ordered_food.quantity = item.quantity
            ordered_food.price = item.fooditem.price
            ordered_food.amount = item.fooditem.price * item.quantity
            ordered_food.save()
        # send notification
        mail_subject = "Thank you for ordering with us!"
        mail_template = "orders/order_confirmation_email.html"
        context = {
            "user": request.user,
            "order": order,
            "to_email": order.email,
        }
        send_notification(mail_subject, mail_template, context)

        # send order email to vendors
        mail_subject = "You received new order!"
        mail_template = "orders/new_order_received.html"
        to_emails = []
        for i in cart_items:
            if i.fooditem.vendor.user.email not in to_emails:
                to_emails.append(i.fooditem.vendor.user.email)
        context = {
            "order": order,
            "to_email": to_emails,
        }
        send_notification(mail_subject, mail_template, context)

        # delete cart if payment success
        cart_items.delete()
        ordered_food = OrderedFood.objects.filter(order=order)
        subtotal = 0
        for item in ordered_food:
            subtotal += item.price + item.quantity
        tax_data = json.loads(order.tax_data)
        context = {
            "order": order,
            "ordered_food": ordered_food,
            "subtotal": subtotal,
            "tax_data": tax_data,
        }
        return render(request, "stripe/payment_success.html", context)


@login_required(login_url="login")
def payment_failed(request):
    session_id = request.GET["session_id"]
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session_data = stripe.checkout.Session.retrieve(
        session_id,
    )
    print(session_data)
    # current_order = Order.objects.get(order_number=current_order_id['current_order_id'])
    # if current_order:
    #    current_order.status = 'Cancelled'
    #    current_order.save()
    return render(request, "stripe/payment_failed.html")
