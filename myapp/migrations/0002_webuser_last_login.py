# Generated by Django 5.1.3 on 2024-11-20 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='webuser',
            name='last_login',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
