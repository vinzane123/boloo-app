# Generated by Django 3.0.3 on 2020-02-08 16:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipments', '0007_delete_bus'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
    ]
