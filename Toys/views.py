from django.shortcuts import render

# Create your views here.
import uuid
from datetime import datetime
from decimal import Decimal

from django.db.models import Q
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

from Toys.tasks import send_mail
from Toys.forms import OrderForm
from Toys.models import *


def create_cart():
    new_cart = Cart()
    new_cart.save()
    cart_id = new_cart.id

    cart_filter = CartFilter(cart_id=cart_id)
    cart_filter.save()
    return cart_id


@cache_page(10)  # 10 sec
def home(request):
    # cache.set('test', 'test value')

    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    try:
        cart_id = request.session['cart_id']
    except KeyError:
        cart_id = create_cart().hex
        request.session['cart_id'] = cart_id

    if cart_id is None or Cart.objects.all().filter(id=cart_id).count() == 0:
        cart_id = create_cart().hex
        request.session['cart_id'] = cart_id

    toys = Toy.objects.all().filter(
        ~Q(id__in=CartItem.objects.all().filter(cart_id=cart_id).values_list('item_id')))

    # Producer filter
    cart_producer_filter = CartProducerFilter.objects.all().filter(cart_id=cart_id)
    if cart_producer_filter:
        toys = toys.filter(producer__id__in=cart_producer_filter.values_list('producer_id'))

    # Other filters
    cart_filter = CartFilter.objects.all().filter(cart_id=cart_id).first()
    if cart_filter.age_from is not None:
        toys = toys.filter(age__gte=cart_filter.age_from)
    if cart_filter.age_to is not None:
        toys = toys.filter(age__lte=cart_filter.age_to)

    if cart_filter.price_from is not None:
        toys = toys.filter(price__gte=cart_filter.price_from)
    if cart_filter.price_to is not None:
        toys = toys.filter(price__lte=cart_filter.price_to)

    return render(
        request,
        'index.html',
        {
            'year': datetime.now().year,
            'number_in_cart': CartItem.objects.all().filter(cart_id=cart_id).__len__(),
            'toys': toys,
            'producers': Producer.objects.all(),
            'filtered_producers': cart_producer_filter.values_list('producer_id', flat=True),
            'age_from': cart_filter.age_from if cart_filter.age_from is not None else '',
            'age_to': cart_filter.age_to if cart_filter.age_to is not None else '',
            'price_from': cart_filter.price_from if cart_filter.price_from is not None else '',
            'price_to': cart_filter.price_to if cart_filter.price_to is not None else '',
        }
    )


def order(request):
    """Renders the order page."""
    assert isinstance(request, HttpRequest)
    cart_id = request.session['cart_id']
    cart = Cart.objects.get(pk=cart_id)
    cart_items = CartItem.objects.all().filter(cart_id=cart_id)
    return render(
        request,
        'order.html',
        {
            'number_in_cart': cart_items.__len__(),
            'cart_items': cart_items,
            'total_price': cart.price_total,
            'form': None
        }
    )


@csrf_exempt
def complete(request):
    # if request.method == 'POST':
    form = OrderForm(request.POST)

    cart_id = request.session['cart_id']
    cart = Cart.objects.get(pk=cart_id)
    cart_items = CartItem.objects.all().filter(cart_id=cart_id)
    if form.is_valid():
        o = Order(name=form.cleaned_data['name'], email=form.cleaned_data['email'],
                  phone=form.cleaned_data['phone'], address=form.cleaned_data['address'],
                  price_total=cart.price_total)
        o.save()

        for cart_item in cart_items:
            oi = OrderItem(order=o, item=Toy.objects.get(pk=cart_item.item.id), number=cart_item.number)
            oi.save()

        cart.delete()
       # send_mail.apply_async((o.name, price))
        send_mail(o.name, o.email, o.phone, o.price_total)
        return HttpResponseRedirect('/home')

    return render(
        request,
        'order.html',
        {
            'number_in_cart': cart_items.__len__(),
            'cart_items': cart_items,
            'total_price': cart.price_total,
            'form': form
        }
    )


@csrf_exempt
def buy(request, toy_id, number):
    assert isinstance(request, HttpRequest)
    cart_id = request.session['cart_id']
    cart = Cart.objects.get(pk=cart_id)
    if CartItem.objects.all().filter(cart_id=cart_id).count() == 0:
        cart.price_total = 0

    added_price = Toy.objects.get(pk=toy_id).price * int(number)
    cart_item = CartItem(cart_id=cart_id, item_id=toy_id, number=number, price=added_price)
    cart_item.save()

    cart.price_total += added_price
    cart.save()

    return HttpResponseRedirect('/')


@csrf_exempt
def remove(request, toy_id):
    assert isinstance(request, HttpRequest)
    cart_id = request.session['cart_id']
    cart = Cart.objects.get(pk=cart_id)
    remove_price = CartItem.objects.get(cart_id=cart_id, item_id=toy_id).price
    cart.price_total -=remove_price
    cart.save()
    CartItem.objects.get(cart_id=cart_id, item_id=toy_id).delete()

    if CartItem.objects.all().filter(cart_id=cart_id).count() == 0:
        cart.price_total = 0
        return HttpResponseRedirect('/')

    return HttpResponseRedirect('/order')


@csrf_exempt
def producer(request, producer_id, is_for_add):
    cart_id = request.session['cart_id']
    if is_for_add == 'true':
        cart_producer_filter = CartProducerFilter(cart_id=cart_id, producer_id=producer_id)
        cart_producer_filter.save()
    else:
        CartProducerFilter.objects.all().filter(cart_id=cart_id).filter(producer_id=producer_id).delete()
    return HttpResponseRedirect('/')


@csrf_exempt
def update_filter(request, parameter, from_to, value):
    assert isinstance(request, HttpRequest)

    cart_id = request.session['cart_id']
    cart_filter = CartFilter.objects.get(cart_id=cart_id)
    if parameter == 'age':
        if from_to == 'from':
            cart_filter.age_from = int(value) if value != '-1' else None
        else:
            cart_filter.age_to = int(value) if value != '-1' else None
    elif parameter == 'price':
        if from_to == 'from':
            cart_filter.price_from = Decimal(value) if value != '-1' else None
        else:
            cart_filter.price_to = Decimal(value) if value != '-1' else None
    cart_filter.save()

    return HttpResponseRedirect('/')


@csrf_exempt
def login(request):
    return render(
        request,
        'login.html',
        ''
    )
