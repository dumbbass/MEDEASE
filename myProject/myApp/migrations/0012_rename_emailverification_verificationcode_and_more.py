# Generated by Django 5.1.6 on 2025-05-13 03:51

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0011_emailverification'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='EmailVerification',
            new_name='VerificationCode',
        ),
        migrations.AlterModelOptions(
            name='verificationcode',
            options={},
        ),
    ]
