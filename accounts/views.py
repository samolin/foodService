from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import UserForm
from .models import User, UserProfile
from vendor.forms import VendorForm


def registerUser(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            user = form.save(commit=False)
            user.set_password(password)
            user.role = User.CUSTOMER
            user.save()
            messages.success(request, 'Account has been created successfully!')
            return redirect('registerUser')
        else:
            print(form.errors)
    else:
        form = UserForm()
    context = {
        'form': form,
    }
    return render(request, 'accounts/registerUser.html', context)


def registerVendor(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        vendor_form = VendorForm(request.POST, request.FILES)
        if form.is_valid() and vendor_form.is_valid():
            password = form.cleaned_data['password']
            user = form.save(commit=False)
            user.set_password(password)
            user.role = User.VENDOR
            user.save()
            vendor = vendor_form.save(commit=False)
            vendor.user = user
            user_profile = UserProfile.objects.get(user=user)
            vendor.user_profile = user_profile
            vendor.save()
            messages.success(request, 'Account has been created successfully! Please wait for approval.')
            return redirect('registerVendor')
        else:
            print(form.errors)
    else:    
        form = UserForm()
        vendor_form = VendorForm()
    context = {
        'form': form,
        'vendor_form': vendor_form,
    }
    return render(request, 'accounts/registerVendor.html', context)
