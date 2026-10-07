from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0004_sync_pay_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='评价内容')),
                ('rating', models.IntegerField(verbose_name='评分')),
                ('is_approved', models.BooleanField(default=False, verbose_name='审核通过')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='评价时间')),
                ('goods', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.goods', verbose_name='关联商品')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='core.order', verbose_name='关联订单')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='评价用户')),
            ],
            options={
                'verbose_name': '商品评价',
                'verbose_name_plural': '商品评价',
            },
        ),
    ]
