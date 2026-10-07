from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# 用户扩展模型（关联Django自带User）
class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, verbose_name='关联用户')
    nickname = models.CharField(max_length=50, null=True, blank=True, verbose_name='昵称')
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatar/', null=True, blank=True, verbose_name='头像')
    school = models.CharField(max_length=50, null=True, blank=True, verbose_name='学校')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    def update_profile(self, nickname=None, avatar=None, mobile=None, school=None):
        """更新扩展信息：昵称、头像、手机号、学校（只能更新当前profile字段，不改User表字段除昵称外）。"""
        changed = False
        if nickname is not None:
            self.nickname = nickname
            changed = True
        if avatar is not None:
            self.avatar = avatar
            changed = True
        if mobile is not None:
            self.mobile = mobile
            changed = True
        if school is not None:
            self.school = school
            changed = True
        if changed:
            self.save()
        return self

    def set_password(self, raw_password):
        """通过 User 对象封装修改登录密码的逻辑。"""
        self.user.set_password(raw_password)
        self.user.save()

    class Meta:
        verbose_name = '用户扩展'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.nickname or self.user.username


# 商品分类模型
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='分类名称')
    desc = models.TextField(null=True, blank=True, verbose_name='分类描述')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '商品分类'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']  # 按创建时间倒序排列
    
    def __str__(self):
        """返回分类名称，用于Admin后台和模型显示"""
        return self.name


class Address(models.Model):
    """用户收货地址模型，支持多地址与默认地址标记"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='addresses', verbose_name='所属用户')
    recipient = models.CharField(max_length=60, verbose_name='收件人')
    phone = models.CharField(max_length=20, verbose_name='联系电话')
    province = models.CharField(max_length=50, null=True, blank=True, verbose_name='省')
    city = models.CharField(max_length=50, null=True, blank=True, verbose_name='市')
    district = models.CharField(max_length=50, null=True, blank=True, verbose_name='区/县')
    detail = models.CharField(max_length=255, verbose_name='详细地址')
    is_default = models.BooleanField(default=False, verbose_name='默认地址')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '收货地址'
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        # 如果设置为默认地址，则把该用户的其他地址设为非默认
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.recipient} {self.phone}'


# 二手商品模型（含AI字段）
class Goods(models.Model):
    STATUS_CHOICES = (
        (0, '待上架'),
        (1, '在售'),
        (2, '已售出'),
    )
    title = models.CharField(max_length=100, verbose_name='商品标题')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    desc = models.TextField(verbose_name='商品描述')
    image = models.ImageField(upload_to='goods/', null=True, blank=True, verbose_name='商品图片')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='所属分类')
    seller = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='卖家')
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name='商品状态')
    stock = models.PositiveIntegerField(default=1, verbose_name='库存')
    is_sold = models.BooleanField(default=False, verbose_name='已售出')
    ai_description = models.TextField(null=True, blank=True, verbose_name='AI生成描述')
    ai_price_suggestion = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='AI价格建议')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '二手商品'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


# 订单模型
class Order(models.Model):
    STATUS_CHOICES = (
        (0, '待付款'),
        (1, '已付款'),
        (2, '已完成'),
        (3, '已取消'),
    )
    order_no = models.CharField(max_length=32, unique=True, verbose_name='订单号')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='关联商品')
    buyer = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='买家')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='收货地址')
    quantity = models.PositiveIntegerField(default=1, verbose_name='购买数量')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='订单金额')
    # 支付状态：0=未支付，1=已支付，2=已取消
    PAY_STATUS_UNPAID = 0
    PAY_STATUS_PAID = 1
    PAY_STATUS_CANCELLED = 2

    PAY_STATUS_CHOICES = (
        (PAY_STATUS_UNPAID, '未支付'),
        (PAY_STATUS_PAID, '已支付'),
        (PAY_STATUS_CANCELLED, '已取消'),
    )
    pay_status = models.IntegerField(choices=PAY_STATUS_CHOICES, default=PAY_STATUS_UNPAID, verbose_name='支付状态')
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name='订单状态')
    # 新增：更细化的订单流转状态（兼容旧字段 status）
    ORDER_STATUS_PENDING = 0
    ORDER_STATUS_PAID = 1
    ORDER_STATUS_PENDING_DELIVERY = 2
    ORDER_STATUS_DELIVERED = 3
    ORDER_STATUS_COMPLETED = 4
    ORDER_STATUS_CANCELLED = 5

    ORDER_STATUS_CHOICES = (
        (ORDER_STATUS_PENDING, '待支付'),
        (ORDER_STATUS_PAID, '已支付'),
        (ORDER_STATUS_PENDING_DELIVERY, '待发货'),
        (ORDER_STATUS_DELIVERED, '已发货'),
        (ORDER_STATUS_COMPLETED, '已完成'),
        (ORDER_STATUS_CANCELLED, '已取消'),
    )

    order_status = models.IntegerField(choices=ORDER_STATUS_CHOICES, default=ORDER_STATUS_PENDING, verbose_name='订单流转状态')

    AFTERSALE_STATUS_NONE = 0
    AFTERSALE_STATUS_REQUESTED = 1
    AFTERSALE_STATUS_APPROVED = 2
    AFTERSALE_STATUS_REJECTED = 3
    AFTERSALE_STATUS_COMPLETED = 4

    AFTERSALE_STATUS_CHOICES = (
        (AFTERSALE_STATUS_NONE, '无售后'),
        (AFTERSALE_STATUS_REQUESTED, '售后申请中'),
        (AFTERSALE_STATUS_APPROVED, '卖家已同意'),
        (AFTERSALE_STATUS_REJECTED, '卖家已拒绝'),
        (AFTERSALE_STATUS_COMPLETED, '售后已完成'),
    )

    AFTERSALE_TYPE_REFUND = 'refund'
    AFTERSALE_TYPE_RETURN_REFUND = 'return_refund'
    AFTERSALE_TYPE_EXCHANGE = 'exchange'
    AFTERSALE_TYPE_REPAIR = 'repair'

    AFTERSALE_TYPE_CHOICES = (
        (AFTERSALE_TYPE_REFUND, '仅退款'),
        (AFTERSALE_TYPE_RETURN_REFUND, '退货退款'),
        (AFTERSALE_TYPE_EXCHANGE, '换货'),
        (AFTERSALE_TYPE_REPAIR, '维修/补发'),
    )

    # 物流相关字段（保留现有 company/no 字段并增加合并信息字段）
    logistics_no = models.CharField(max_length=128, null=True, blank=True, verbose_name='物流单号')
    logistics_company = models.CharField(max_length=64, null=True, blank=True, verbose_name='物流公司')
    logistics_info = models.CharField(max_length=255, null=True, blank=True, verbose_name='物流信息')
    deliver_time = models.DateTimeField(null=True, blank=True, verbose_name='发货时间')
    confirm_time = models.DateTimeField(null=True, blank=True, verbose_name='确认收货时间')
    cancel_reason = models.TextField(null=True, blank=True, verbose_name='取消原因')
    aftersale_status = models.IntegerField(choices=AFTERSALE_STATUS_CHOICES, default=AFTERSALE_STATUS_NONE, verbose_name='售后状态')
    aftersale_type = models.CharField(max_length=32, choices=AFTERSALE_TYPE_CHOICES, null=True, blank=True, verbose_name='售后类型')
    aftersale_reason = models.TextField(null=True, blank=True, verbose_name='售后原因')
    aftersale_reply = models.TextField(null=True, blank=True, verbose_name='卖家处理说明')
    aftersale_apply_time = models.DateTimeField(null=True, blank=True, verbose_name='售后申请时间')
    aftersale_handle_time = models.DateTimeField(null=True, blank=True, verbose_name='售后处理时间')
    aftersale_finish_time = models.DateTimeField(null=True, blank=True, verbose_name='售后完成时间')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '订单'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.order_no

    def mark_as_delivered(self, company=None, logistics_no=None):
        """标记为已发货：仅在已支付状态下允许。"""
        if self.pay_status != self.PAY_STATUS_PAID:
            raise ValueError('订单未支付，无法标记发货')
        if self.order_status not in [self.ORDER_STATUS_PAID, self.ORDER_STATUS_PENDING_DELIVERY]:
            raise ValueError('当前订单状态不允许发货')
        self.logistics_company = company
        self.logistics_no = logistics_no
        # 兼容性：填写合并物流信息字段
        if company or logistics_no:
            parts = []
            if company:
                parts.append(company)
            if logistics_no:
                parts.append(logistics_no)
            self.logistics_info = ' '.join(parts)
        self.deliver_time = timezone.now()
        self.order_status = self.ORDER_STATUS_DELIVERED
        self.status = 1
        self.save(update_fields=['logistics_company', 'logistics_no', 'logistics_info', 'deliver_time', 'order_status', 'status'])

    def mark_as_completed(self):
        """标记为已完成（确认收货）。"""
        if self.order_status != self.ORDER_STATUS_DELIVERED:
            raise ValueError('订单未发货或状态不正确，无法确认收货')
        self.confirm_time = timezone.now()
        self.order_status = self.ORDER_STATUS_COMPLETED
        self.status = 2
        # 库存售罄后标记商品为已售出并更新商品状态
        try:
            g = self.goods
            if g.stock <= 0:
                g.status = 2  # 已售出
                g.is_sold = True
                g.save(update_fields=['status', 'is_sold'])
        except Exception:
            pass

        self.save(update_fields=['confirm_time', 'order_status', 'status'])

    def can_cancel(self):
        """判断订单是否可取消，仅当订单状态为「待支付」或「已支付」时返回True"""
        return self.order_status in [self.ORDER_STATUS_PENDING, self.ORDER_STATUS_PAID]

    def can_apply_aftersale(self):
        """已发货或已完成的已支付订单可发起售后；卖家拒绝后允许买家重新提交。"""
        return (
            self.pay_status == self.PAY_STATUS_PAID
            and self.order_status in [self.ORDER_STATUS_DELIVERED, self.ORDER_STATUS_COMPLETED]
            and self.aftersale_status in [self.AFTERSALE_STATUS_NONE, self.AFTERSALE_STATUS_REJECTED]
        )

    def apply_aftersale(self, aftersale_type, reason):
        if not self.can_apply_aftersale():
            raise ValueError('当前订单状态不支持申请售后')
        self.aftersale_type = aftersale_type
        self.aftersale_reason = reason
        self.aftersale_reply = ''
        self.aftersale_status = self.AFTERSALE_STATUS_REQUESTED
        self.aftersale_apply_time = timezone.now()
        self.aftersale_handle_time = None
        self.aftersale_finish_time = None
        self.save(update_fields=[
            'aftersale_type',
            'aftersale_reason',
            'aftersale_reply',
            'aftersale_status',
            'aftersale_apply_time',
            'aftersale_handle_time',
            'aftersale_finish_time',
        ])

    def handle_aftersale(self, approved, reply=''):
        if self.aftersale_status != self.AFTERSALE_STATUS_REQUESTED:
            raise ValueError('当前订单没有待处理的售后申请')
        self.aftersale_status = self.AFTERSALE_STATUS_APPROVED if approved else self.AFTERSALE_STATUS_REJECTED
        self.aftersale_reply = reply
        self.aftersale_handle_time = timezone.now()
        self.save(update_fields=['aftersale_status', 'aftersale_reply', 'aftersale_handle_time'])

    def complete_aftersale(self):
        if self.aftersale_status != self.AFTERSALE_STATUS_APPROVED:
            raise ValueError('卖家同意后才能确认售后完成')
        self.aftersale_status = self.AFTERSALE_STATUS_COMPLETED
        self.aftersale_finish_time = timezone.now()
        self.save(update_fields=['aftersale_status', 'aftersale_finish_time'])


class Comment(models.Model):
    """商品评价模型

    - `order` 使用 OneToOneField 确保一个订单只能评价一次
    - 在保存时会校验：订单属于该用户、订单关联的商品一致、订单已支付
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, verbose_name='评价用户')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, verbose_name='关联商品')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, verbose_name='关联订单')
    content = models.TextField(verbose_name='评价内容')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='评分')
    is_approved = models.BooleanField(default=False, verbose_name='审核通过')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评价时间')

    class Meta:
        verbose_name = '商品评价'
        verbose_name_plural = verbose_name

    def clean(self):
        if self.order.buyer_id != self.user_id:
            raise ValidationError('该订单不属于当前用户，无法评价')
        if self.order.goods_id != self.goods_id:
            raise ValidationError('订单和商品不匹配')
        if self.order.pay_status != Order.PAY_STATUS_PAID:
            raise ValidationError('订单未支付，无法评价')
        if self.order.order_status != Order.ORDER_STATUS_COMPLETED:
            raise ValidationError('订单未完成，无法评价')

    def save(self, *args, **kwargs):
        # 在保存前进行校验，保证数据一致性
        self.full_clean()
        super().save(*args, **kwargs)

    def approve(self):
        """管理员/系统调用：通过审核"""
        if not self.is_approved:
            self.is_approved = True
            self.save(update_fields=['is_approved'])

    def reject(self):
        """管理员/系统调用：驳回审核"""
        if self.is_approved:
            self.is_approved = False
            self.save(update_fields=['is_approved'])


class Favorite(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='favorites', verbose_name='用户')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='商品')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='收藏时间')

    class Meta:
        verbose_name = '收藏'
        verbose_name_plural = verbose_name
        unique_together = ('user', 'goods')
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.user.username} - {self.goods.title}'


class GoodsReport(models.Model):
    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_REJECTED = 2

    STATUS_CHOICES = (
        (STATUS_PENDING, '待处理'),
        (STATUS_APPROVED, '已处理'),
        (STATUS_REJECTED, '已驳回'),
    )

    REASON_QUALITY = 'quality_issue'
    REASON_FAKE = 'fake_or_fraud'
    REASON_PRICE = 'price_dispute'
    REASON_ILLEGAL = 'illegal_content'
    REASON_OTHER = 'other'

    REASON_CHOICES = (
        (REASON_QUALITY, '商品描述不符/质量问题'),
        (REASON_FAKE, '疑似虚假信息/欺诈'),
        (REASON_PRICE, '价格争议'),
        (REASON_ILLEGAL, '违规内容'),
        (REASON_OTHER, '其他'),
    )

    reporter = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='goods_reports', verbose_name='举报人')
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, related_name='reports', verbose_name='被举报商品')
    reason = models.CharField(max_length=32, choices=REASON_CHOICES, verbose_name='举报原因')
    detail = models.TextField(blank=True, null=True, verbose_name='补充说明')
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='处理状态')
    admin_reply = models.TextField(blank=True, null=True, verbose_name='处理备注')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='举报时间')
    handle_time = models.DateTimeField(blank=True, null=True, verbose_name='处理时间')

    class Meta:
        verbose_name = '商品举报'
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.reporter.username} 举报 {self.goods.title}'
