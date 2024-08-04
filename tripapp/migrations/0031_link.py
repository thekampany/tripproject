# Generated by Django 4.2.14 on 2024-08-04 09:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tripapp', '0030_delete_link'),
    ]

    operations = [
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(blank=True, null=True)),
                ('document', models.FileField(blank=True, null=True, upload_to='documents/')),
                ('day_program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='tripapp.dayprogram')),
            ],
        ),
    ]
