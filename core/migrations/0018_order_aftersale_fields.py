from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_normalize_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='aftersale_status',
            field=models.IntegerField(
                choices=[
                    (0, '无售后'),
                    (1, '售后申请中'),
                    (2, '卖家已同意'),
                    (3, '卖家已拒绝'),
                    (4, '售后已完成'),
                ],
                default=0,
                verbose_name='售后状态',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='aftersale_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('refund', '仅退款'),
                    ('return_refund', '退货退款'),
                    ('exchange', '换货'),
                    ('repair', '维修/补发'),
                ],
                max_length=32,
                null=True,
                verbose_name='售后类型',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='aftersale_reason',
            field=models.TextField(blank=True, null=True, verbose_name='售后原因'),
        ),
        migrations.AddField(
            model_name='order',
            name='aftersale_reply',
            field=models.TextField(blank=True, null=True, verbose_name='卖家处理说明'),
        ),
        migrations.AddField(
            model_name='order',
            name='aftersale_apply_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='售后申请时间'),
        ),
        migrations.AddField(
            model_name='order',
            name='aftersale_handle_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='售后处理时间'),
        ),
        migrations.AddField(
            model_name='order',
            name='aftersale_finish_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='售后完成时间'),
        ),
    ]
