
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tripapp', '0046_tripper_currency_tripbudget'),
    ]

    operations = [
        migrations.AddField(
            model_name='tripbudget',
            name='currency',
            field=models.CharField(max_length=10, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tripbudget',
            name='converted_amount',
            field=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tripper',
            name='currency',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
