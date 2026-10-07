from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_order_status_and_logistics'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='logistics_info',
            field=models.CharField(max_length=255, null=True, blank=True, verbose_name='物流信息'),
        ),
        migrations.AddField(
            model_name='goods',
            name='is_sold',
            field=models.BooleanField(default=False, verbose_name='已售出'),
        ),
    ]
