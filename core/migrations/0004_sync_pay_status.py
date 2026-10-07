from django.db import migrations


def set_status_from_pay_status(apps, schema_editor):
    Order = apps.get_model('core', 'Order')
    # 将 pay_status == 1 的订单的 status 设为 1 (已付款)
    orders = Order.objects.filter(pay_status=1)
    for o in orders:
        o.status = 1
        o.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_add_pay_status'),
    ]

    operations = [
        migrations.RunPython(set_status_from_pay_status, reverse_code=migrations.RunPython.noop),
    ]
