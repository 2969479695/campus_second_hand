from django.contrib import admin
from django.utils import timezone

from .models import Category, Comment, Favorite, Goods, GoodsReport, Order, UserProfile


# 注册用户扩展模型
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile', 'avatar', 'create_time')  # 列表显示字段
    search_fields = ('user__username', 'mobile')  # 搜索字段（关联用户的用户名）
    list_filter = ('create_time',)  # 筛选字段


# 注册商品分类模型（关键修改：移除fieldsets中的create_time）
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_desc_preview', 'create_time')  # 列表仍显示create_time（仅展示，不可编辑）
    search_fields = ('name', 'desc')  # 搜索字段
    list_filter = ('create_time',)  # 筛选字段
    list_per_page = 20  # 每页显示数量
    ordering = ['-create_time']  # 默认排序
    
    exclude = ['create_time']
    # 修改：仅保留可编辑的基本信息，删除包含create_time的时间信息模块
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'desc')
        }),
        # 移除了错误的「时间信息」模块（包含create_time）
    )
    
    def get_desc_preview(self, obj):
        """显示描述预览（截取前50个字符）"""
        if obj.desc:
            return obj.desc[:50] + '...' if len(obj.desc) > 50 else obj.desc
        return '-'
    get_desc_preview.short_description = '分类描述'


# 注册二手商品模型
@admin.register(Goods)
class GoodsAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'category', 'seller', 'status', 'create_time')
    search_fields = ('title', 'seller__username')
    list_filter = ('status', 'category', 'create_time')
    readonly_fields = ('ai_description', 'ai_price_suggestion')  # AI字段只读


# 注册订单模型
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'goods', 'buyer', 'quantity', 'amount', 'status', 'pay_status', 'order_status', 'logistics_company', 'logistics_no', 'deliver_time', 'confirm_time', 'create_time')
    search_fields = ('order_no', 'buyer__username')
    list_filter = ('order_status', 'status', 'create_time')
    actions = ['mark_delivered_action', 'mark_completed_action']

    def mark_delivered_action(self, request, queryset):
        updated = 0
        for o in queryset:
            try:
                if getattr(o, 'order_status', None) == o.ORDER_STATUS_PAID:
                    o.mark_as_delivered(company=o.logistics_company or 'Admin', logistics_no=o.logistics_no or '')
                    updated += 1
            except Exception:
                continue
        self.message_user(request, f'已标记发货 {updated} 个订单')
    mark_delivered_action.short_description = '批量标记为已发货'

    def mark_completed_action(self, request, queryset):
        updated = 0
        for o in queryset:
            try:
                if getattr(o, 'order_status', None) == o.ORDER_STATUS_DELIVERED:
                    o.mark_as_completed()
                    updated += 1
            except Exception:
                continue
        self.message_user(request, f'已标记完成 {updated} 个订单')
    mark_completed_action.short_description = '批量标记为已完成'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    # 展示：评价用户、商品、评分、审核状态、评价时间
    list_display = ('user', 'goods', 'rating', 'is_approved', 'created_at')
    search_fields = ('user__username', 'goods__title', 'order__order_no')
    # 筛选：按审核状态、商品、评价时间
    list_filter = ('is_approved', 'goods', 'created_at')
    list_per_page = 25
    ordering = ['-created_at']
    actions = ['approve_comments', 'reject_comments']

    def approve_comments(self, request, queryset):
        for c in queryset:
            c.approve()
        self.message_user(request, f'已通过 {queryset.count()} 条评价')
    approve_comments.short_description = '通过所选评价'

    def reject_comments(self, request, queryset):
        for c in queryset:
            c.reject()
        self.message_user(request, f'已驳回 {queryset.count()} 条评价')
    reject_comments.short_description = '驳回所选评价'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'goods', 'create_time')
    search_fields = ('user__username', 'goods__title')
    list_filter = ('create_time',)


@admin.register(GoodsReport)
class GoodsReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'goods', 'reason', 'status', 'create_time', 'handle_time')
    search_fields = ('reporter__username', 'goods__title', 'detail')
    list_filter = ('status', 'reason', 'create_time')
    actions = ['mark_report_approved', 'mark_report_rejected']

    def mark_report_approved(self, request, queryset):
        updated = queryset.update(status=GoodsReport.STATUS_APPROVED, handle_time=timezone.now())
        self.message_user(request, f'已标记处理 {updated} 条举报')
    mark_report_approved.short_description = '标记为已处理'

    def mark_report_rejected(self, request, queryset):
        updated = queryset.update(status=GoodsReport.STATUS_REJECTED, handle_time=timezone.now())
        self.message_user(request, f'已驳回 {updated} 条举报')
    mark_report_rejected.short_description = '标记为已驳回'
