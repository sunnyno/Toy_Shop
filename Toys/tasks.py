# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
import yagmail


@shared_task
def send_mail(name, email, phone, price_total):

    yag = yagmail.SMTP('toyshop.web.lab', 'qwerty1111')

    yag.send(email, 'New toy order', 'Hello, '+name+'! '+
             "You have done a new order at ToyShop. "
             "You phone number is "+phone+
             ". Total price is "+str(price_total)+
             ". We will contact you soon!"
             " Thank you!"
             " Best regards,"
             " ToyShop Team")
