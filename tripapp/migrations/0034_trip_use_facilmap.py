# Generated by Django 4.2.14 on 2024-08-07 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tripapp', '0033_route'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='use_facilmap',
            field=models.BooleanField(default=False),
        ),
    ]
