from django.contrib import admin
from .models import displayed_items

# Register your models here.
@admin.register(displayed_items)
class DisplayedItems(admin.ModelAdmin):
    list_display = ('barcode','display_name','display_color','variable_price')

