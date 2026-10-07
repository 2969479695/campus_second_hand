from datetime import timedelta

from django.db import migrations
from django.utils import timezone


DESIRED_CATEGORIES = [
    '二手书籍',
    '床上用品',
    '体育用品',
    '数码产品',
    '其他',
]


def normalize_categories(apps, schema_editor):
    Category = apps.get_model('core', 'Category')
    Goods = apps.get_model('core', 'Goods')

    other, _ = Category.objects.get_or_create(
        name='其他',
        defaults={'desc': '其他类型的校园闲置商品'},
    )

    Category.objects.filter(name__in=DESIRED_CATEGORIES).update(desc='')
    other.desc = '其他类型的校园闲置商品'
    other.save(update_fields=['desc'])

    Goods.objects.exclude(category__name__in=DESIRED_CATEGORIES).update(category=other)
    Category.objects.exclude(name__in=DESIRED_CATEGORIES).delete()

    base_time = timezone.now()
    for index, name in enumerate(DESIRED_CATEGORIES):
        category, _ = Category.objects.get_or_create(name=name)
        category.create_time = base_time - timedelta(minutes=index)
        category.save(update_fields=['create_time'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_order_address_quantity'),
    ]

    operations = [
        migrations.RunPython(normalize_categories, migrations.RunPython.noop),
    ]
