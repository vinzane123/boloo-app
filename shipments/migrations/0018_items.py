# Generated by Django 3.0.3 on 2020-02-10 21:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipments', '0017_auto_20200208_2154'),
    ]

    operations = [
        migrations.CreateModel(
            name='Items',
            fields=[
                ('id', models.IntegerField(default=None, primary_key=True, serialize=False, unique=True)),
                ('data', models.TextField(default=None)),
                ('status', models.TextField(default='Open')),
            ],
        ),
    ]
