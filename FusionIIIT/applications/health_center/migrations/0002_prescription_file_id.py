# Generated by Django 3.1.5 on 2024-04-15 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('health_center', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='prescription',
            name='file_id',
            field=models.IntegerField(default=0),
        ),
    ]
