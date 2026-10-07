from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_add_favorite'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GoodsReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('quality_issue', '商品描述不符/质量问题'), ('fake_or_fraud', '疑似虚假信息/欺诈'), ('price_dispute', '价格争议'), ('illegal_content', '违规内容'), ('other', '其他')], max_length=32, verbose_name='举报原因')),
                ('detail', models.TextField(blank=True, null=True, verbose_name='补充说明')),
                ('status', models.IntegerField(choices=[(0, '待处理'), (1, '已处理'), (2, '已驳回')], default=0, verbose_name='处理状态')),
                ('admin_reply', models.TextField(blank=True, null=True, verbose_name='处理备注')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='举报时间')),
                ('handle_time', models.DateTimeField(blank=True, null=True, verbose_name='处理时间')),
                ('goods', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='core.goods', verbose_name='被举报商品')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='goods_reports', to=settings.AUTH_USER_MODEL, verbose_name='举报人')),
            ],
            options={
                'verbose_name': '商品举报',
                'verbose_name_plural': '商品举报',
                'ordering': ['-create_time'],
            },
        ),
    ]
