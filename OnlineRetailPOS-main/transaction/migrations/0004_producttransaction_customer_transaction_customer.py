# Generated by Django 4.1.13 on 2025-01-07 05:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transaction', '0003_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='producttransaction',
            name='customer',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.RESTRICT, to='transaction.customer'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='customer',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.RESTRICT, to='transaction.customer'),
        ),
    ]
