from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Avg, Count, Max, Min, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

import random
import string

from .forms import GoodsForm, LoginForm, RegisterForm
from .models import Address, Category, Comment, Favorite, Goods, GoodsReport, Order, UserProfile


RUNNING_ORDER_STATUSES = [
    Order.ORDER_STATUS_PENDING,
    Order.ORDER_STATUS_PAID,
    Order.ORDER_STATUS_PENDING_DELIVERY,
    Order.ORDER_STATUS_DELIVERED,
]


def generate_order_no():
    timestamp = str(int(timezone.now().timestamp()))
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'{timestamp}{random_str}'


def get_order_by_identifier(identifier, lock=False):
    qs = Order.objects.select_for_update() if lock else Order.objects
    try:
        return qs.get(order_no=identifier)
    except Order.DoesNotExist:
        pass

    try:
        order_id = int(identifier)
    except (TypeError, ValueError):
        return None

    try:
        return qs.get(id=order_id)
    except Order.DoesNotExist:
        return None


def index(request):
    goods_list = Goods.objects.filter(status=1, stock__gt=0).select_related('category', 'seller').order_by('-create_time')[:8]
    return render(request, 'core/index.html', {'goods_list': goods_list})


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            mobile = form.cleaned_data['mobile']
            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=username, password=password)
                    UserProfile.objects.create(user=user, mobile=mobile)
                messages.success(request, '注册成功！请登录')
                return redirect('core:login')
            except Exception as exc:
                messages.error(request, f'注册失败：{str(exc)}')
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('core:index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is None:
                messages.error(request, '用户名或密码错误，请重试')
            else:
                login(request, user)
                messages.success(request, f'欢迎回来，{username}！')
                return redirect('core:index')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.success(request, '您已成功退出')
    return redirect('core:login')


@login_required(login_url='core:login')
def goods_publish(request):
    if request.method == 'POST':
        form = GoodsForm(request.POST, request.FILES)
        if form.is_valid():
            goods = form.save(commit=False)
            goods.seller = request.user
            goods.status = 1
            if goods.stock <= 0:
                goods.stock = 1
            goods.save()
            messages.success(request, '商品发布成功！')
            return redirect('core:goods_detail', goods_id=goods.id)
    else:
        form = GoodsForm()

    return render(request, 'core/goods_publish.html', {'form': form})


def goods_list(request):
    goods_qs = Goods.objects.filter(status=1, stock__gt=0).select_related('category', 'seller')
    categories = Category.objects.all()

    category_id = request.GET.get('category')
    keyword = (request.GET.get('q') or '').strip()
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort', 'latest')

    if category_id:
        goods_qs = goods_qs.filter(category_id=category_id)

    if keyword:
        goods_qs = goods_qs.filter(Q(title__icontains=keyword) | Q(desc__icontains=keyword) | Q(category__name__icontains=keyword))

    if min_price:
        try:
            goods_qs = goods_qs.filter(price__gte=min_price)
        except Exception:
            min_price = ''

    if max_price:
        try:
            goods_qs = goods_qs.filter(price__lte=max_price)
        except Exception:
            max_price = ''

    if sort == 'price_asc':
        goods_qs = goods_qs.order_by('price', '-create_time')
    elif sort == 'price_desc':
        goods_qs = goods_qs.order_by('-price', '-create_time')
    else:
        sort = 'latest'
        goods_qs = goods_qs.order_by('-create_time')

    favorite_goods_ids = set()
    if request.user.is_authenticated:
        favorite_goods_ids = set(Favorite.objects.filter(user=request.user, goods_id__in=goods_qs.values_list('id', flat=True)).values_list('goods_id', flat=True))

    context = {
        'goods_list': goods_qs,
        'categories': categories,
        'current_category': int(category_id) if category_id and category_id.isdigit() else None,
        'q': keyword,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'sort': sort,
        'favorite_goods_ids': favorite_goods_ids,
    }
    return render(request, 'core/goods_list.html', context)


def goods_detail(request, goods_id):
    goods = get_object_or_404(Goods.objects.select_related('seller', 'category'), id=goods_id)

    can_comment = False
    eligible_order_id = None
    if request.user.is_authenticated:
        eligible_order = (
            Order.objects.filter(
                goods=goods,
                buyer=request.user,
                pay_status=Order.PAY_STATUS_PAID,
                order_status=Order.ORDER_STATUS_COMPLETED,
                comment__isnull=True,
            )
            .order_by('-create_time')
            .first()
        )
        if eligible_order:
            can_comment = True
            eligible_order_id = eligible_order.id

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, goods=goods).exists()

    return render(
        request,
        'core/goods_detail.html',
        {
            'goods': goods,
            'can_comment': can_comment,
            'eligible_order_id': eligible_order_id,
            'is_favorited': is_favorited,
            'report_reason_choices': GoodsReport.REASON_CHOICES,
        },
    )


@login_required(login_url='core:login')
def order_create(request, goods_id):
    default_address = Address.objects.filter(user=request.user).order_by('-is_default', '-update_time').first()
    if not default_address:
        messages.error(request, '请先添加收货地址后再购买')
        return redirect('core:personal_center')

    ok, result = _create_order_for_user(request.user, goods_id, quantity=1, address_id=default_address.id)
    if not ok:
        messages.error(request, result)
        return redirect('core:goods_detail', goods_id=goods_id)

    messages.success(request, '订单创建成功！')
    return redirect('core:order_list')


def _create_order_for_user(user, goods_id, quantity=1, address_id=None):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return False, '购买数量格式不正确'
    if quantity <= 0:
        return False, '购买数量必须大于0'

    address = None
    if address_id:
        try:
            address = Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            return False, '请选择有效的收货地址'

    with transaction.atomic():
        goods = get_object_or_404(Goods.objects.select_for_update(), id=goods_id)

        if goods.seller_id == user.id:
            return False, '不能购买自己发布的商品'

        if goods.status != 1 or goods.is_sold:
            return False, '该商品已下架或已售出，无法购买'

        if goods.stock < quantity:
            return False, '该商品库存不足，无法购买'

        existing_order = Order.objects.filter(
            goods=goods,
            buyer=user,
            order_status__in=RUNNING_ORDER_STATUSES,
        ).exists()
        if existing_order:
            return False, '您已对该商品创建过进行中的订单，请前往订单列表查看'

        order_no = generate_order_no()
        while Order.objects.filter(order_no=order_no).exists():
            order_no = generate_order_no()

        order = Order.objects.create(
            order_no=order_no,
            goods=goods,
            buyer=user,
            address=address,
            quantity=quantity,
            amount=goods.price * quantity,
            pay_status=Order.PAY_STATUS_UNPAID,
            status=0,
            order_status=Order.ORDER_STATUS_PENDING,
        )

        goods.stock -= quantity
        if goods.stock == 0:
            goods.status = 0
        goods.save(update_fields=['stock', 'status'])

    return True, order


@login_required(login_url='core:login')
@require_GET
def api_addresses(request):
    addresses = request.user.addresses.all().order_by('-is_default', '-update_time')
    data = [
        {
            'id': addr.id,
            'recipient': addr.recipient,
            'phone': addr.phone,
            'province': addr.province or '',
            'city': addr.city or '',
            'district': addr.district or '',
            'detail': addr.detail,
            'is_default': addr.is_default,
        }
        for addr in addresses
    ]
    return JsonResponse({'success': True, 'addresses': data})


@login_required(login_url='core:login')
@require_POST
def api_order_create(request):
    goods_id = request.POST.get('goods_id')
    address_id = request.POST.get('address_id')
    quantity = request.POST.get('quantity') or 1
    if not goods_id:
        return JsonResponse({'success': False, 'message': '缺少商品ID'}, status=400)
    if not address_id:
        return JsonResponse({'success': False, 'message': '请选择收货地址'}, status=400)

    ok, result = _create_order_for_user(request.user, goods_id, quantity=quantity, address_id=address_id)
    if not ok:
        return JsonResponse({'success': False, 'message': result}, status=400)

    return JsonResponse(
        {
            'success': True,
            'message': '订单创建成功',
            'order_id': result.id,
            'order_no': result.order_no,
        }
    )


@login_required(login_url='core:login')
def order_list(request):
    orders = Order.objects.filter(buyer=request.user).select_related('goods', 'goods__category', 'goods__seller').order_by('-create_time')
    comment_order_ids = list(Comment.objects.filter(user=request.user, order__in=orders).values_list('order_id', flat=True))
    return render(request, 'core/order_list.html', {'orders': orders, 'comment_order_ids': comment_order_ids})


@login_required(login_url='core:login')
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def order_pay(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        if not order_id:
            return render(request, 'core/pay.html', {'error': '缺少 order_id 参数'})

        order = get_order_by_identifier(order_id, lock=False)
        if not order or order.buyer_id != request.user.id:
            return render(request, 'core/pay.html', {'error': '订单不存在或无权限'})

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return render(request, 'core/pay_fragment.html', {'order': order})
        return render(request, 'core/pay.html', {'order': order})

    order_id = request.POST.get('order_id')
    if not order_id:
        return JsonResponse({'success': False, 'message': '缺少 order_id 参数'}, status=400)

    order = get_order_by_identifier(order_id, lock=True)
    if not order:
        return JsonResponse({'success': False, 'message': '订单不存在'}, status=404)
    if order.buyer_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该订单'}, status=403)
    if order.order_status == Order.ORDER_STATUS_CANCELLED:
        return JsonResponse({'success': False, 'message': '订单已取消，无法支付'}, status=400)
    if order.pay_status == Order.PAY_STATUS_PAID:
        return JsonResponse({'success': False, 'message': '订单已支付'}, status=400)
    if order.pay_status == Order.PAY_STATUS_CANCELLED:
        return JsonResponse({'success': False, 'message': '订单已取消，无法支付'}, status=400)
    if order.order_status != Order.ORDER_STATUS_PENDING:
        return JsonResponse({'success': False, 'message': '订单状态不支持支付'}, status=400)

    order.pay_status = Order.PAY_STATUS_PAID
    order.order_status = Order.ORDER_STATUS_PAID
    order.status = 1
    order.save(update_fields=['pay_status', 'order_status', 'status'])
    return JsonResponse({'success': True, 'message': '支付成功'})


@login_required(login_url='core:login')
def my_goods(request):
    goods_qs = Goods.objects.filter(seller=request.user).prefetch_related('order_set').order_by('-create_time')
    return render(request, 'core/my_goods.html', {'goods_list': goods_qs})


@login_required(login_url='core:login')
def goods_edit(request, goods_id):
    goods = get_object_or_404(Goods, id=goods_id, seller=request.user)
    if request.method == 'POST':
        form = GoodsForm(request.POST, request.FILES, instance=goods)
        if form.is_valid():
            goods = form.save(commit=False)
            goods.status = 1 if goods.stock > 0 else 0
            goods.is_sold = False
            goods.save()
            messages.success(request, '商品已更新并重新上架！')
            return redirect('core:my_goods')
    else:
        form = GoodsForm(instance=goods)
    return render(request, 'core/goods_edit.html', {'form': form, 'goods': goods})


@login_required(login_url='core:login')
@require_POST
def delist_goods(request, goods_id):
    goods = get_object_or_404(Goods, id=goods_id)
    if goods.seller_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该商品'}, status=403)

    has_running_order = Order.objects.filter(
        goods=goods,
        order_status__in=RUNNING_ORDER_STATUSES,
    ).exists()
    if has_running_order:
        return JsonResponse({'success': False, 'message': '该商品存在进行中的订单，无法下架'}, status=400)

    goods.status = 0
    goods.save(update_fields=['status'])
    return JsonResponse({'success': True, 'message': '商品已下架'})


@login_required(login_url='core:login')
@require_POST
def mark_order_delivered(request, order_id):
    order = get_object_or_404(Order.objects.select_related('goods'), id=order_id)
    if order.goods.seller_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该订单'}, status=403)

    if order.order_status != Order.ORDER_STATUS_PAID:
        return JsonResponse({'success': False, 'message': '仅已支付订单可标记发货'}, status=400)

    company = (request.POST.get('company') or '').strip()
    logistics_no = (request.POST.get('logistics_no') or '').strip()
    if not company or not logistics_no:
        return JsonResponse({'success': False, 'message': '请填写物流公司与单号'}, status=400)

    try:
        with transaction.atomic():
            order.mark_as_delivered(company=company, logistics_no=logistics_no)
        return JsonResponse({'success': True, 'message': '已标记为发货'})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': f'标记发货失败: {str(exc)}'}, status=500)


@login_required(login_url='core:login')
def deliver_fragment(request, order_id):
    order = get_object_or_404(Order.objects.select_related('goods', 'address'), id=order_id)
    if order.goods.seller_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权查看'}, status=403)
    return render(request, 'core/deliver_fragment.html', {'order': order})


@login_required(login_url='core:login')
@require_POST
def confirm_order_received(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.buyer_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该订单'}, status=403)
    if order.aftersale_status == Order.AFTERSALE_STATUS_REQUESTED:
        return JsonResponse({'success': False, 'message': '该订单存在待处理售后，暂不能确认收货'}, status=400)
    if order.order_status != Order.ORDER_STATUS_DELIVERED:
        return JsonResponse({'success': False, 'message': '订单不是已发货状态，无法确认收货'}, status=400)

    try:
        with transaction.atomic():
            order.mark_as_completed()
        return JsonResponse({'success': True, 'message': '确认收货成功'})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': f'确认收货失败: {str(exc)}'}, status=500)


@login_required(login_url='core:login')
@require_POST
def apply_after_sale(request, order_id):
    order = get_object_or_404(Order.objects.select_related('goods'), id=order_id)
    if order.buyer_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该订单'}, status=403)

    aftersale_type = (request.POST.get('aftersale_type') or '').strip()
    reason = (request.POST.get('reason') or '').strip()
    type_values = [item[0] for item in Order.AFTERSALE_TYPE_CHOICES]
    if aftersale_type not in type_values:
        return JsonResponse({'success': False, 'message': '请选择有效的售后类型'}, status=400)
    if len(reason) < 5:
        return JsonResponse({'success': False, 'message': '请填写至少5个字的售后原因'}, status=400)

    try:
        with transaction.atomic():
            locked_order = Order.objects.select_for_update().get(id=order.id)
            locked_order.apply_aftersale(aftersale_type, reason)
        return JsonResponse({'success': True, 'message': '售后申请已提交，请等待卖家处理'})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@login_required(login_url='core:login')
@require_POST
def handle_after_sale(request, order_id):
    order = get_object_or_404(Order.objects.select_related('goods'), id=order_id)
    if order.goods.seller_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权处理该售后申请'}, status=403)

    action = (request.POST.get('action') or '').strip()
    reply = (request.POST.get('reply') or '').strip()
    if action not in ['approve', 'reject']:
        return JsonResponse({'success': False, 'message': '请选择同意或拒绝'}, status=400)
    if action == 'reject' and len(reply) < 3:
        return JsonResponse({'success': False, 'message': '拒绝售后时请填写处理说明'}, status=400)

    try:
        with transaction.atomic():
            locked_order = Order.objects.select_for_update().get(id=order.id)
            locked_order.handle_aftersale(action == 'approve', reply)
        message = '已同意售后，请等待买家确认完成' if action == 'approve' else '已拒绝售后申请'
        return JsonResponse({'success': True, 'message': message})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@login_required(login_url='core:login')
@require_POST
def complete_after_sale(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.buyer_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该订单'}, status=403)

    try:
        with transaction.atomic():
            locked_order = Order.objects.select_for_update().get(id=order.id)
            locked_order.complete_aftersale()
        return JsonResponse({'success': True, 'message': '售后已确认完成'})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


def _cancel_order_core(order, cancel_reason):
    if not order.can_cancel():
        return False, '该订单无法取消'

    with transaction.atomic():
        order.order_status = Order.ORDER_STATUS_CANCELLED
        order.status = 3
        order.cancel_reason = cancel_reason
        order.pay_status = Order.PAY_STATUS_CANCELLED
        order.save(update_fields=['order_status', 'status', 'cancel_reason', 'pay_status'])

        goods = order.goods
        if not goods.is_sold:
            goods.stock += order.quantity
            if goods.status == 0:
                goods.status = 1
            goods.save(update_fields=['stock', 'status'])

    return True, '订单已取消'


def _seller_cancel_order_core(order, cancel_reason):
    if order.order_status not in [
        Order.ORDER_STATUS_PENDING,
        Order.ORDER_STATUS_PAID,
        Order.ORDER_STATUS_PENDING_DELIVERY,
    ]:
        return False, '该订单已发货或已完成，请通过售后流程处理'

    if order.aftersale_status in [
        Order.AFTERSALE_STATUS_REQUESTED,
        Order.AFTERSALE_STATUS_APPROVED,
    ]:
        return False, '该订单存在进行中的售后，暂不能直接取消'

    reason = cancel_reason or '卖家取消订单'
    if order.pay_status == Order.PAY_STATUS_PAID:
        reason = f'{reason}（已支付订单已模拟退款）'

    with transaction.atomic():
        order.order_status = Order.ORDER_STATUS_CANCELLED
        order.status = 3
        order.cancel_reason = reason
        order.pay_status = Order.PAY_STATUS_CANCELLED
        order.save(update_fields=['order_status', 'status', 'cancel_reason', 'pay_status'])

        goods = order.goods
        if not goods.is_sold:
            goods.stock += order.quantity
            if goods.status == 0:
                goods.status = 1
            goods.save(update_fields=['stock', 'status'])

    return True, '卖家已取消订单'


@login_required(login_url='core:login')
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.buyer_id != request.user.id:
        messages.error(request, '无权操作该订单')
        return redirect('core:order_list')

    if request.method == 'POST':
        ok, message = _cancel_order_core(order, (request.POST.get('cancel_reason') or '').strip())
        if ok:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('core:order_list')

    return render(request, 'core/cancel_order.html', {'order': order})


@login_required(login_url='core:login')
@require_POST
def seller_cancel_order_ajax(request, order_id):
    order = get_object_or_404(Order.objects.select_related('goods'), id=order_id)
    if order.goods.seller_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权取消该订单'}, status=403)

    ok, message = _seller_cancel_order_core(order, (request.POST.get('cancel_reason') or '').strip())
    if ok:
        return JsonResponse({'success': True, 'message': message})
    return JsonResponse({'success': False, 'message': message}, status=400)


@login_required(login_url='core:login')
@require_POST
def cancel_order_ajax(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.buyer_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该订单'}, status=403)

    ok, message = _cancel_order_core(order, (request.POST.get('cancel_reason') or '').strip())
    if ok:
        return JsonResponse({'success': True, 'message': message})
    return JsonResponse({'success': False, 'message': message}, status=400)


@login_required(login_url='core:login')
@require_POST
def delete_order_ajax(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.buyer_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权操作该订单'}, status=403)

    if order.order_status != Order.ORDER_STATUS_CANCELLED:
        return JsonResponse({'success': False, 'message': '只能删除已取消的订单'}, status=400)

    order.delete()
    return JsonResponse({'success': True, 'message': '订单已删除'})


@login_required(login_url='core:login')
@require_POST
def add_comment(request):
    rating = request.POST.get('rating')
    content = (request.POST.get('content') or '').strip()
    goods_id = request.POST.get('goods_id')
    order_id = request.POST.get('order_id')

    if not all([rating, content, goods_id, order_id]):
        return JsonResponse({'success': False, 'message': '缺少参数'}, status=400)

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': '评分格式错误'}, status=400)

    if rating < 1 or rating > 5:
        return JsonResponse({'success': False, 'message': '评分必须在1到5之间'}, status=400)

    order = get_order_by_identifier(order_id)
    if not order:
        return JsonResponse({'success': False, 'message': '订单不存在'}, status=404)

    if order.buyer_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权对该订单评价'}, status=403)

    if str(order.goods_id) != str(goods_id):
        return JsonResponse({'success': False, 'message': '订单与商品不匹配'}, status=400)

    if order.pay_status != Order.PAY_STATUS_PAID:
        return JsonResponse({'success': False, 'message': '订单未支付，无法评价'}, status=400)
    if order.order_status != Order.ORDER_STATUS_COMPLETED:
        return JsonResponse({'success': False, 'message': '订单未完成，无法评价'}, status=400)

    if Comment.objects.filter(order=order).exists():
        return JsonResponse({'success': False, 'message': '该订单已评价'}, status=400)

    comment = Comment.objects.create(
        user=request.user,
        goods_id=goods_id,
        order=order,
        content=content,
        rating=rating,
        is_approved=True,
    )
    return JsonResponse({'success': True, 'message': '评价成功', 'comment_id': comment.id})


@require_GET
def get_goods_comments(request, goods_id=None):
    goods_id = goods_id or request.GET.get('goods_id') or request.GET.get('id')
    if not goods_id:
        return JsonResponse({'success': False, 'message': '缺少 goods_id'}, status=400)

    comments = Comment.objects.filter(goods_id=goods_id, is_approved=True).select_related('user').order_by('-created_at')
    data = [
        {
            'id': c.id,
            'user': c.user.username if c.user else None,
            'rating': c.rating,
            'content': c.content,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M'),
        }
        for c in comments
    ]
    return JsonResponse({'success': True, 'comments': data})


@login_required(login_url='core:login')
def my_comments(request):
    comments = Comment.objects.filter(user=request.user).select_related('goods').order_by('-created_at')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = [
            {
                'id': c.id,
                'goods_title': c.goods.title if c.goods else '',
                'rating': c.rating,
                'content': c.content,
                'is_approved': c.is_approved,
                'created_at': c.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            for c in comments
        ]
        return JsonResponse({'success': True, 'comments': data})
    return render(request, 'core/my_comments.html', {'comments': comments})


@login_required(login_url='core:login')
@require_POST
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user_id != request.user.id:
        return JsonResponse({'success': False, 'message': '无权修改该评论'}, status=403)
    if comment.is_approved:
        return JsonResponse({'success': False, 'message': '已审核的评论不能修改'}, status=400)

    rating = request.POST.get('rating')
    content = (request.POST.get('content') or '').strip()
    if not rating or not content:
        return JsonResponse({'success': False, 'message': '缺少参数'}, status=400)

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': '评分格式错误'}, status=400)

    if rating < 1 or rating > 5:
        return JsonResponse({'success': False, 'message': '评分必须在1到5之间'}, status=400)

    comment.rating = rating
    comment.content = content
    comment.save()
    return JsonResponse({'success': True, 'message': '修改成功'})


@login_required(login_url='core:login')
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user, defaults={'mobile': ''})
    addresses = request.user.addresses.all().order_by('-is_default', '-update_time')

    counts = {
        'pending': Order.objects.filter(buyer=request.user, order_status=Order.ORDER_STATUS_PENDING).count(),
        'paid': Order.objects.filter(buyer=request.user, order_status=Order.ORDER_STATUS_PAID).count(),
        'delivered': Order.objects.filter(buyer=request.user, order_status=Order.ORDER_STATUS_DELIVERED).count(),
        'completed': Order.objects.filter(buyer=request.user, order_status=Order.ORDER_STATUS_COMPLETED).count(),
    }

    return render(request, 'core/profile.html', {'profile': profile_obj, 'addresses': addresses, 'counts': counts})


@login_required(login_url='core:login')
def personal_center(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user, defaults={'mobile': ''})
    addresses = request.user.addresses.all().order_by('-is_default', '-update_time')
    return render(
        request,
        'core/personal_center.html',
        {
            'profile': profile_obj,
            'addresses': addresses,
            'active_tab': request.GET.get('tab', 'profile'),
        },
    )


@login_required(login_url='core:login')
@require_POST
def update_avatar(request):
    avatar_file = request.FILES.get('avatar')
    if not avatar_file:
        return JsonResponse({'success': False, 'message': '请选择头像文件'})

    if avatar_file.content_type not in ['image/jpeg', 'image/png', 'image/gif']:
        return JsonResponse({'success': False, 'message': '只支持 JPG、PNG、GIF 格式的图片'})
    if avatar_file.size > 2 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': '图片大小不能超过 2MB'})

    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user, defaults={'mobile': ''})
    profile_obj.avatar = avatar_file
    profile_obj.save(update_fields=['avatar'])
    return JsonResponse({'success': True, 'message': '头像更新成功', 'avatar_url': profile_obj.avatar.url})


@login_required(login_url='core:login')
@require_POST
def update_profile(request):
    nickname = (request.POST.get('nickname') or '').strip()
    school = (request.POST.get('school') or '').strip()

    if nickname and len(nickname) > 10:
        return JsonResponse({'success': False, 'message': '昵称长度不能超过10个字符'})

    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user, defaults={'mobile': ''})
    profile_obj.update_profile(nickname=nickname, school=school)
    return JsonResponse({'success': True, 'message': '信息更新成功'})


@login_required(login_url='core:login')
@require_POST
def update_password(request):
    old_password = request.POST.get('old_password')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')

    if not all([old_password, new_password, confirm_password]):
        return JsonResponse({'success': False, 'message': '请填写所有密码字段'})

    if not request.user.check_password(old_password):
        return JsonResponse({'success': False, 'message': '原密码错误'})

    if len(new_password) < 6 or len(new_password) > 20:
        return JsonResponse({'success': False, 'message': '新密码长度必须在6-20位之间'})

    has_letter = any(c.isalpha() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)
    if not (has_letter and has_digit):
        return JsonResponse({'success': False, 'message': '新密码必须包含字母和数字'})

    if new_password != confirm_password:
        return JsonResponse({'success': False, 'message': '两次输入的新密码不一致'})

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)
    return JsonResponse({'success': True, 'message': '密码修改成功'})


@login_required(login_url='core:login')
def manage_address(request):
    if request.method == 'GET':
        addresses = request.user.addresses.all().order_by('-is_default', '-update_time')
        return render(request, 'core/manage_address.html', {'addresses': addresses})

    action = request.POST.get('action')
    if action == 'add':
        return _address_add_from_payload(request)
    if action == 'edit':
        return _address_edit_from_payload(request)
    if action == 'delete':
        return _address_delete_from_payload(request)
    if action == 'set_default':
        return _address_set_default_from_payload(request)
    return JsonResponse({'success': False, 'message': '无效的操作'}, status=400)


@login_required(login_url='core:login')
@require_POST
def add_address(request):
    return _address_add_from_payload(request)


@login_required(login_url='core:login')
@require_POST
def edit_address(request, addr_id):
    return _address_edit_from_payload(request, address_id=addr_id)


@login_required(login_url='core:login')
@require_POST
def delete_address(request, addr_id):
    return _address_delete_from_payload(request, address_id=addr_id)


@login_required(login_url='core:login')
@require_POST
def set_default_address(request, addr_id):
    return _address_set_default_from_payload(request, address_id=addr_id)


@login_required(login_url='core:login')
def address_fragment(request, addr_id):
    addr = get_object_or_404(Address, id=addr_id, user=request.user)
    return render(request, 'core/address_fragment.html', {'addr': addr})


@login_required(login_url='core:login')
def address_detail(request, addr_id):
    addr = get_object_or_404(Address, id=addr_id, user=request.user)
    return JsonResponse(
        {
            'success': True,
            'address': {
                'id': addr.id,
                'recipient': addr.recipient,
                'phone': addr.phone,
                'province': addr.province,
                'city': addr.city,
                'district': addr.district,
                'detail': addr.detail,
                'is_default': addr.is_default,
            },
        }
    )


def _clean_address_data(request):
    return {
        'recipient': (request.POST.get('recipient') or '').strip(),
        'phone': (request.POST.get('phone') or '').strip(),
        'province': (request.POST.get('province') or '').strip(),
        'city': (request.POST.get('city') or '').strip(),
        'district': (request.POST.get('district') or '').strip(),
        'detail': (request.POST.get('detail') or '').strip(),
        'is_default': request.POST.get('is_default') in ['1', 'true', 'on'],
    }


def _validate_address_data(data):
    if not data['recipient'] or not data['phone'] or not data['detail']:
        return False, '请填写收件人、电话和详细地址'
    if not data['phone'].isdigit() or len(data['phone']) < 6:
        return False, '请输入有效联系电话'
    return True, ''


def _address_add_from_payload(request):
    data = _clean_address_data(request)
    ok, message = _validate_address_data(data)
    if not ok:
        return JsonResponse({'success': False, 'message': message}, status=400)

    addr = Address.objects.create(user=request.user, **data)
    return JsonResponse({'success': True, 'message': '地址添加成功', 'address_id': addr.id})


def _address_edit_from_payload(request, address_id=None):
    address_id = address_id or request.POST.get('address_id')
    if not address_id:
        return JsonResponse({'success': False, 'message': '缺少地址ID'}, status=400)

    addr = get_object_or_404(Address, id=address_id, user=request.user)
    data = _clean_address_data(request)
    ok, message = _validate_address_data(data)
    if not ok:
        return JsonResponse({'success': False, 'message': message}, status=400)

    for key, value in data.items():
        setattr(addr, key, value)
    addr.save()
    return JsonResponse({'success': True, 'message': '地址修改成功'})


def _address_delete_from_payload(request, address_id=None):
    address_id = address_id or request.POST.get('address_id')
    if not address_id:
        return JsonResponse({'success': False, 'message': '缺少地址ID'}, status=400)

    addr = get_object_or_404(Address, id=address_id, user=request.user)
    addr.delete()
    return JsonResponse({'success': True, 'message': '地址删除成功'})


def _address_set_default_from_payload(request, address_id=None):
    address_id = address_id or request.POST.get('address_id')
    if not address_id:
        return JsonResponse({'success': False, 'message': '缺少地址ID'}, status=400)

    addr = get_object_or_404(Address, id=address_id, user=request.user)
    addr.is_default = True
    addr.save(update_fields=['is_default'])
    return JsonResponse({'success': True, 'message': '已设为默认地址'})


@login_required(login_url='core:login')
@require_POST
def toggle_favorite(request, goods_id):
    goods = get_object_or_404(Goods, id=goods_id)
    fav, created = Favorite.objects.get_or_create(user=request.user, goods=goods)
    if created:
        return JsonResponse({'success': True, 'is_favorited': True, 'message': '已加入收藏'})
    fav.delete()
    return JsonResponse({'success': True, 'is_favorited': False, 'message': '已取消收藏'})


@login_required(login_url='core:login')
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('goods', 'goods__category').order_by('-create_time')
    return render(request, 'core/favorite_list.html', {'favorites': favorites})


@login_required(login_url='core:login')
@require_POST
def add_goods_report(request, goods_id):
    goods = get_object_or_404(Goods, id=goods_id)
    if goods.seller_id == request.user.id:
        return JsonResponse({'success': False, 'message': '不能举报自己发布的商品'}, status=400)

    reason = (request.POST.get('reason') or '').strip()
    detail = (request.POST.get('detail') or '').strip()
    reason_values = [item[0] for item in GoodsReport.REASON_CHOICES]
    if reason not in reason_values:
        return JsonResponse({'success': False, 'message': '请选择有效的举报原因'}, status=400)

    # 一天内对同一商品只允许提交一次待处理举报，避免刷举报
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    has_pending = GoodsReport.objects.filter(
        reporter=request.user,
        goods=goods,
        status=GoodsReport.STATUS_PENDING,
        create_time__gte=today_start,
    ).exists()
    if has_pending:
        return JsonResponse({'success': False, 'message': '你今天已举报过该商品，请等待处理结果'}, status=400)

    report = GoodsReport.objects.create(
        reporter=request.user,
        goods=goods,
        reason=reason,
        detail=detail,
    )
    return JsonResponse({'success': True, 'message': '举报提交成功，平台将尽快处理', 'report_id': report.id})


@login_required(login_url='core:login')
def my_reports(request):
    reports = GoodsReport.objects.filter(reporter=request.user).select_related('goods').order_by('-create_time')
    return render(request, 'core/my_reports.html', {'reports': reports})


# ============================================================================
#  数据统计（平台运营看板）
# ----------------------------------------------------------------------------
#  该视图把平台业务数据汇总成三部分：
#    ① 核心指标卡片：商品/订单/用户/评价的总量与结构
#    ② 订单漏斗：从下单到完成各状态的数量与占比
#    ③ 分类与趋势：各分类供给与成交、商品发布趋势、商品热度排行
#  技术要点：用 Django ORM 的聚合函数（Count / Sum / Avg / Max / Min）
#            在数据库侧完成统计，而不是把数据取到 Python 里再循环。
# ============================================================================
def statistics(request):
    """平台运营数据看板：展示商品、订单、用户、评价的统计结果。"""
    today = timezone.now().date()

    # ---------------- 商品统计 ----------------
    # 注意：Goods.STATUS_CHOICES 为 (0,待上架)(1,在售)(2,已售出)，
    # 模型未定义命名常量，这里沿用项目既有的裸整数写法
    goods_total = Goods.objects.count()
    goods_on_sale = Goods.objects.filter(status=1).count()
    goods_sold = Goods.objects.filter(status=2).count()
    goods_pending = Goods.objects.filter(status=0).count()
    goods_out_of_stock = Goods.objects.filter(stock=0).count()
    price_stats = Goods.objects.aggregate(
        avg=Avg('price'), max=Max('price'), min=Min('price'), total=Sum('price')
    )
    # 今日新增商品
    goods_today = Goods.objects.filter(create_time__date=today).count()

    # ---------------- 订单统计 ----------------
    order_total = Order.objects.count()
    order_finished = Order.objects.filter(order_status=Order.ORDER_STATUS_COMPLETED).count()
    order_cancelled = Order.objects.filter(order_status=Order.ORDER_STATUS_CANCELLED).count()
    order_running = Order.objects.filter(order_status__in=RUNNING_ORDER_STATUSES).count()
    amount_stats = Order.objects.filter(
        order_status=Order.ORDER_STATUS_COMPLETED
    ).aggregate(total=Sum('amount'), avg=Avg('amount'), max=Max('amount'))
    # 成交率 = 已完成订单 / 全部订单
    finish_rate = round(order_finished * 100.0 / order_total, 1) if order_total else 0

    # ---------------- 用户与评价 ----------------
    user_total = User.objects.count()
    comment_total = Comment.objects.count()
    rating_avg = Comment.objects.aggregate(avg=Avg('rating'))['avg']
    favorite_total = Favorite.objects.count()
    report_total = GoodsReport.objects.count()
    report_pending = GoodsReport.objects.filter(
        status=GoodsReport.STATUS_PENDING).count()

    # ---------------- 订单状态分布（用于漏斗/柱状图）----------------
    status_labels = dict(Order.ORDER_STATUS_CHOICES)
    status_rows = (Order.objects.values('order_status')
                   .annotate(n=Count('id')).order_by('order_status'))
    order_status_data = [
        {'label': status_labels.get(r['order_status'], '未知'),
         'value': r['n'],
         'percent': round(r['n'] * 100.0 / order_total, 1) if order_total else 0}
        for r in status_rows
    ]

    # ---------------- 各分类统计 ----------------
    categories = []
    for c in Category.objects.annotate(
            n=Count('goods'), avg_price=Avg('goods__price')).order_by('-n', 'name'):
        # 该分类下已完成订单的成交额
        revenue = (Order.objects
                   .filter(order_status=Order.ORDER_STATUS_COMPLETED,
                           goods__category=c)
                   .aggregate(s=Sum('amount'))['s']) or 0
        categories.append({
            'name': c.name,
            'count': c.n,
            'avg_price': round(c.avg_price, 2) if c.avg_price else 0,
            'revenue': revenue,
        })

    # ---------------- 商品发布趋势（按月）----------------
    monthly = {}
    for g in Goods.objects.values('create_time'):
        if not g['create_time']:
            continue
        key = g['create_time'].strftime('%Y-%m')
        monthly[key] = monthly.get(key, 0) + 1
    monthly_trend = [{'month': k, 'count': monthly[k]} for k in sorted(monthly)]

    # ---------------- 商品热度排行 ----------------
    # 注意：Order.goods 的反向查询名是 order（不是 order_set / orders）
    hot_goods = (Goods.objects
                 .annotate(fav=Count('favorited_by', distinct=True),
                           sold=Count('order', distinct=True))
                 .select_related('category')
                 .order_by('-fav', '-sold', '-price')[:5])
    hot_goods_data = [{
        'title': g.title[:14],
        'price': float(g.price or 0),
        'fav': g.fav,
        'sold': g.sold,
        'category': g.category.name if g.category else '未分类',
    } for g in hot_goods]

    # ---------------- 价格区间分布 ----------------
    segments = [('0-50 元', 0, 50), ('50-200 元', 50, 200),
                ('200-1000 元', 200, 1000), ('1000-5000 元', 1000, 5000),
                ('5000 元以上', 5000, None)]
    price_segments = []
    for label, low, high in segments:
        qs = Goods.objects.filter(price__gte=low)
        if high is not None:
            qs = qs.filter(price__lt=high)
        price_segments.append({'label': label, 'count': qs.count()})

    # ---------------- 汇总给模板 ----------------
    # 图表数据用 json_script 输出（模板中 |json_script:"xxx"），
    # 避免手工拼 JSON 字符串，既安全（自动转义）又不用写 |safe
    context = {
        'goods_total': goods_total,
        'goods_on_sale': goods_on_sale,
        'goods_sold': goods_sold,
        'goods_pending': goods_pending,
        'goods_out_of_stock': goods_out_of_stock,
        'goods_today': goods_today,
        'avg_price': round(price_stats['avg'], 2) if price_stats['avg'] else 0,
        'max_price': price_stats['max'] or 0,
        'min_price': price_stats['min'] or 0,
        'price_total': price_stats['total'] or 0,

        'order_total': order_total,
        'order_finished': order_finished,
        'order_cancelled': order_cancelled,
        'order_running': order_running,
        'finish_rate': finish_rate,
        'amount_total': amount_stats['total'] or 0,
        'amount_avg': round(amount_stats['avg'], 2) if amount_stats['avg'] else 0,
        'amount_max': amount_stats['max'] or 0,
        'order_status_data': order_status_data,

        'user_total': user_total,
        'comment_total': comment_total,
        'rating_avg': round(rating_avg, 2) if rating_avg else 0,
        'favorite_total': favorite_total,
        'report_total': report_total,
        'report_pending': report_pending,

        'categories': categories,
        'monthly_trend': monthly_trend,
        'hot_goods_data': hot_goods_data,
        'price_segments': price_segments,

        # ---- 图表专用的纯数组（供 json_script 输出给 Chart.js）----
        'chart_order_labels': [d['label'] for d in order_status_data],
        'chart_order_values': [d['value'] for d in order_status_data],
        'chart_order_percents': [d['percent'] for d in order_status_data],
        'chart_cat_names': [c['name'] for c in categories],
        'chart_cat_counts': [c['count'] for c in categories],
        'chart_cat_avg': [float(c['avg_price']) for c in categories],
        'chart_price_labels': [p['label'] for p in price_segments],
        'chart_price_counts': [p['count'] for p in price_segments],
        'chart_trend_months': [m['month'] for m in monthly_trend],
        'chart_trend_counts': [m['count'] for m in monthly_trend],
    }
    return render(request, 'core/statistics.html', context)
