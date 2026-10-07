from django.db import migrations, models
import django.db.models.deletion



class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_order_status_and_logistics'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_status',
            field=models.IntegerField(choices=[(0, '待支付'), (1, '已支付'), (2, '已发货'), (3, '已完成'), (4, '已取消')], default=0, verbose_name='订单流转状态'),
        ),
        migrations.AddField(
            model_name='order',
            name='logistics_no',
            field=models.CharField(max_length=128, null=True, blank=True, verbose_name='物流单号'),
        ),
        migrations.AddField(
            model_name='order',
            name='logistics_company',
            field=models.CharField(max_length=64, null=True, blank=True, verbose_name='物流公司'),
        ),
        migrations.AddField(
            model_name='order',
            name='deliver_time',
            field=models.DateTimeField(null=True, blank=True, verbose_name='发货时间'),
        ),
        migrations.AddField(
            model_name='order',
            name='confirm_time',
            field=models.DateTimeField(null=True, blank=True, verbose_name='确认收货时间'),
        ),
        # 数据迁移：将旧的status映射到新的order_status
        migrations.RunSQL(
            sql="""
            UPDATE core_order SET order_status = CASE
                WHEN status = 0 THEN 0
                WHEN status = 1 THEN 1
                WHEN status = 2 THEN 3
                WHEN status = 3 THEN 4
                ELSE 0 END
            WHERE order_status = 0;
            """,
            reverse_sql="""
            -- no-op reverse
            """,
        ),
    ]
