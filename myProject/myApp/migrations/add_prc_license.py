from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0006_medicalrecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='prc_license',
            field=models.CharField(default='', help_text='Professional Regulation Commission License Number', max_length=50, unique=True),
            preserve_default=False,
        ),
    ] 