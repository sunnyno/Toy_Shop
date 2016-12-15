from django.contrib import admin

# Register your models here.

from Toys.models import Producer, Toy


class ProducerAdmin(admin.ModelAdmin):
    list_display = ['name']
admin.site.register(Producer, ProducerAdmin)


class ToyAdmin(admin.ModelAdmin):
    list_display = ['name', 'producer_name', 'age', 'description', 'image']
    list_filter = ['name']
    ordering = ['name']
    list_display_links = ['name', 'producer_name']

    @staticmethod
    def producer_name(obj):
        return obj.producer.name

admin.site.register(Toy, ToyAdmin)
