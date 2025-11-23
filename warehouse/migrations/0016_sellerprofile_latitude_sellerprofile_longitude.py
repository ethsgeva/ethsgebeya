from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0015_alter_analyticsreport_id_alter_category_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sellerprofile',
            name='latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sellerprofile',
            name='longitude',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
