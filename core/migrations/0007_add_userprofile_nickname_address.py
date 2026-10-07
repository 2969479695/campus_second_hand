from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_comment_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='nickname',
            field=models.CharField(max_length=50, null=True, blank=True, verbose_name='昵称'),
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient', models.CharField(max_length=60, verbose_name='收件人')),
                ('phone', models.CharField(max_length=20, verbose_name='联系电话')),
                ('province', models.CharField(max_length=50, null=True, blank=True, verbose_name='省')),
                ('city', models.CharField(max_length=50, null=True, blank=True, verbose_name='市')),
                ('district', models.CharField(max_length=50, null=True, blank=True, verbose_name='区/县')),
                ('detail', models.CharField(max_length=255, verbose_name='详细地址')),
                ('is_default', models.BooleanField(default=False, verbose_name='默认地址')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to=settings.AUTH_USER_MODEL, verbose_name='所属用户')),
            ],
            options={
                'verbose_name': '收货地址',
                'verbose_name_plural': '收货地址',
            },
        ),
    ]
