# Generated by Django 4.2.13 on 2024-06-03 19:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tripapp', '0008_trip_slug'),
    ]

    operations = [
        migrations.CreateModel(
            name='Point',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
            ],
        ),
    ]
