# Generated by Django 3.0.3 on 2020-02-08 21:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipments', '0010_auto_20200208_2116'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shipments',
            name='shipmentId',
            field=models.TextField(unique=True),
        ),
    ]
