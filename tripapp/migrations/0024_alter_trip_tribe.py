# Generated by Django 4.2.13 on 2024-06-22 12:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tripapp', '0023_trip_tribe_userprofile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='tribe',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='tripapp.tribe'),
            preserve_default=False,
        ),
    ]
