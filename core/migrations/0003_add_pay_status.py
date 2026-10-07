from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_category_options_alter_category_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="pay_status",
            field=models.IntegerField(choices=[(0, "未支付"), (1, "已支付"), (2, "已取消")], default=0, verbose_name="支付状态"),
        ),
    ]
