from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.conf import settings

from .forms import OrderForm
from .models import Order, OrderLineItem
from products.models import Product
from wishlist.contexts import wishlist_contents

import stripe


def checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    if request.method == 'POST':
        wishlist = request.session.get('wishlist', {})

        form_data = {
            'full_name': request.POST['full_name'],
            'email': request.POST['email'],
            'phone_number': request.POST['phone_number'],
            'country': request.POST['country'],
            'postcode': request.POST['postcode'],
            'town_or_city': request.POST['town_or_city'],
            'street_address1': request.POST['street_address1'],
            'street_address2': request.POST['street_address2'],
            'county': request.POST['county'],
        }
        order_form = OrderForm(form_data)
        if order_form.is_valid():
            order = order_form.save()
            """ pid = request.POST.get('client_secret').split('_secret')[0]
            order.stripe_pid = pid
            order.original_wishlist = json.dumps(wishlist)
            order.save() """
            for item_id, item_data in wishlist.items():
                try:
                    product = Product.objects.get(id=item_id)

                    if isinstance(item_data, int):
                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=item_data,
                        )
                        order_line_item.save()
                    else:
                        for size, quantity in item_data[
                                'items_by_size'].items():
                            order_line_item = OrderLineItem(
                                order=order,
                                product=product,
                                quantity=quantity,
                                product_size=size,
                            )
                            order_line_item.save()
                except Product.DoesNotExist:
                    messages.error(request, (
                        "Sorry the product in your wishlist is not available now."\
                        "Kindly contact us for assistance!")
                    )
                    order.delete()
                    return redirect(reverse('view_checklist'))

                request.session[
                    'save_info'] = 'save-info' in request.POST
                return redirect(reverse(
                    'checkout_confirm', args=[order.order_number]))
        else:
            messages.error(request, ('Error submitting the form. \
                Please double check your information.'))
    
    else:
        wishlist = request.session.get('wishlist', {})
        if not wishlist:
            messages.error(request, "Oops, seems something in your the checkout list is empty!")
            return redirect(reverse('products'))

        current_wishlist = wishlist_contents(request)
        total = current_wishlist['grand_total']
        stripe_total = round(total * 100)
        stripe.api_key = stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )

    order_form = OrderForm()

    if not stripe_public_key:
        messages.warning(
            request, 'Missing stripe public key, please check your environement variables.!')

    template = 'checkout/checkout.html'
    context = {
        'order_form': order_form,
        'stripe_public_key': stripe_public_key,
        'client_secret': intent.client_secret,
    }

    return render(request, template, context)

def checkout_confirm(request, order_number):

    """
        Successful checkout handling code
    """

    save_info = request.session.get('save_info')
    order = get_object_or_404(Order, order_number=order_number)
    messages.success(request, f'Successful purchase done! \
         Order Number is: {order.order_number} \
         Confirmation email sent to {order.email}.')

    if 'wishlist' in request.session:
        del request.session['wishlist']

    template = 'checkout/checkout_confirm.html'
    context = {
        'order': order,
    }

    return render(request, template, context)