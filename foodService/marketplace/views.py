from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.db.models import Prefetch
from django.http.response import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import date

from vendor.models import Vendor
from menu.models import Category, FoodItem
from .models import Cart
from .context_processors import get_cart_counter, get_cart_amounts
from vendor.models import OpeningHour
from orders.forms import OrderForm
from accounts.models import UserProfile

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe
from django.conf import settings


def marketplace(request):
    vendors = Vendor.objects.filter(is_approved=True, user__is_active=True)
    vendor_count = vendors.count()
    context = {
        "vendors": vendors,
        "vendor_count": vendor_count,
    }
    return render(request, "marketplace/listings.html", context)


def vendor_detail(request, vendor_slug):
    vendor = get_object_or_404(Vendor, vendor_slug=vendor_slug)
    categories = Category.objects.filter(vendor=vendor).prefetch_related(
        Prefetch("fooditems", queryset=FoodItem.objects.filter(is_available=True))
    )
    opening_hours = OpeningHour.objects.filter(vendor=vendor).order_by(
        "day", "-from_hour"
    )
    # Check today day
    today_day = date.today()
    today = today_day.isoweekday()
    current_oppening_hour = OpeningHour.objects.filter(vendor=vendor, day=today)

    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user)
    else:
        cart_items = None
    context = {
        "vendor": vendor,
        "categories": categories,
        "cart_items": cart_items,
        "opening_hours": opening_hours,
        "current_oppening_hour": current_oppening_hour,
    }
    return render(request, "marketplace/vendor_detail.html", context)


def add_to_cart(request, food_id):
    if request.user.is_authenticated:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # Check food item exists
            try:
                fooditem = FoodItem.objects.get(id=food_id)
                # Check if the user is already added food to the cart
                try:
                    chkCart = Cart.objects.get(user=request.user, fooditem=fooditem)
                    # Increase cart quantity
                    chkCart.quantity += 1
                    chkCart.save()
                    return JsonResponse(
                        {
                            "status": "Success",
                            "message": "Increased cart quantity",
                            "cart_counter": get_cart_counter(request),
                            "qty": chkCart.quantity,
                            "cart_amount": get_cart_amounts(request),
                        }
                    )
                except:
                    chkCart = Cart.objects.create(
                        user=request.user, fooditem=fooditem, quantity=1
                    )
                    return JsonResponse(
                        {
                            "status": "Success",
                            "message": "Added the food to the cart",
                            "cart_counter": get_cart_counter(request),
                            "qty": chkCart.quantity,
                            "cart_amount": get_cart_amounts(request),
                        }
                    )

            except:
                return JsonResponse(
                    {"status': 'Failed', 'message': 'This food doesn't exist"}
                )
        else:
            return JsonResponse({"status": "Failed", "message": "Invalid request!"})
    return JsonResponse(
        {"status": "login_required", "message": "Please login to continue"}
    )


def decrease_cart(request, food_id):
    if request.user.is_authenticated:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # Check food item exists
            try:
                fooditem = FoodItem.objects.get(id=food_id)
                # Check if the user is already added food to the cart
                try:
                    chkCart = Cart.objects.get(user=request.user, fooditem=fooditem)
                    if chkCart.quantity > 1:
                        # Decrease cart quantity
                        chkCart.quantity -= 1
                        chkCart.save()
                    else:
                        chkCart.delete()
                        chkCart.quantity = 0
                    return JsonResponse(
                        {
                            "status": "Success",
                            "cart_counter": get_cart_counter(request),
                            "qty": chkCart.quantity,
                            "cart_amount": get_cart_amounts(request),
                        }
                    )
                except:
                    return JsonResponse(
                        {
                            "status": "Failed",
                            "message": "You do not have this item in your cart!",
                        }
                    )

            except:
                return JsonResponse(
                    {"status': 'Failed', 'message': 'This food doesn't exist"}
                )
        else:
            return JsonResponse({"status": "Failed", "message": "Invalid request!"})
    return JsonResponse(
        {"status": "login_required", "message": "Please login to continue"}
    )


@login_required(login_url="login")
def cart(request):
    cart_items = Cart.objects.filter(user=request.user).order_by("created_at")
    context = {
        "cart_items": cart_items,
    }
    return render(request, "marketplace/cart.html", context)


def delete_cart(request, cart_id):
    if request.user.is_authenticated:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            try:
                cart_item = Cart.objects.get(user=request.user, id=cart_id)
                if cart_item:
                    cart_item.delete()
                    return JsonResponse(
                        {
                            "status": "Success",
                            "message": "Cart item has been deleted!",
                            "cart_counter": get_cart_counter(request),
                            "cart_amount": get_cart_amounts(request),
                        }
                    )
            except:
                return JsonResponse(
                    {"status": "Failed", "message": "Cart item is not exist!"}
                )
        else:
            return JsonResponse({"status": "Failed", "message": "Invalid request!"})
    return JsonResponse(
        {"status": "login_required", "message": "Please login to continue"}
    )


def search(request):
    keyword = request.GET["keyword"]
    fetch_vendors_by_fooditems = FoodItem.objects.filter(
        food_title__icontains=keyword, is_available=True
    ).values_list("vendor", flat=True)
    print(fetch_vendors_by_fooditems)
    vendors = Vendor.objects.filter(
        Q(id__in=fetch_vendors_by_fooditems)
        | Q(vendor_name__icontains=keyword, is_approved=True, user__is_active=True)
    )
    vendor_count = vendors.count()
    context = {
        "vendors": vendors,
        "vendor_count": vendor_count,
    }
    return render(request, "marketplace/listings.html", context)


@login_required(login_url="login")
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).order_by("created_at")
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect("marketplace")
    user_profile = UserProfile.objects.get(user=request.user)
    default_values = {
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
        "phone": request.user.phone,
        "email": request.user.email,
        "address": user_profile.address,
        "country": user_profile.country,
        "state": user_profile.state,
        "city": user_profile.city,
        "pin_code": user_profile.zip_code,
    }
    form = OrderForm(initial=default_values)
    context = {
        "form": form,
        "cart_items": cart_items,
    }
    return render(request, "marketplace/checkout.html", context)
