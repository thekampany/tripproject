# Generated by Django 4.2.13 on 2024-06-29 17:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tripapp', '0026_badge_tribe'),
    ]

    operations = [
        migrations.AddField(
            model_name='tripper',
            name='is_trip_admin',
            field=models.BooleanField(default=False),
        ),
    ]
