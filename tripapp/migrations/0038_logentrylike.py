# Generated manually because 0037 was faked
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tripapp', '0037_dayprogram_map_image_dayprogram_overnight_location_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogEntryLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('logentry', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='likes',
                    to='tripapp.logentry'
                )),
                ('tripper', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logentry_likes',
                    to='tripapp.tripper'
                )),
            ],
            options={
                'unique_together': {('logentry', 'tripper', 'emoji')},
            },
        ),
    ]
