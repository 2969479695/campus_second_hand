from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile, Category, Goods


class RegisterForm(forms.Form):
    """用户注册表单"""
    username = forms.CharField(
        max_length=150,
        required=True,
        label='用户名',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入用户名'
        }),
        error_messages={
            'required': '用户名不能为空',
            'max_length': '用户名长度不能超过150个字符'
        }
    )
    password = forms.CharField(
        min_length=8,
        required=True,
        label='密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码（至少8位，含大小写字母和数字）'
        }),
        error_messages={
            'required': '密码不能为空',
            'min_length': '密码长度至少为8位'
        }
    )
    password_confirm = forms.CharField(
        min_length=8,
        required=True,
        label='确认密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请再次输入密码'
        }),
        error_messages={
            'required': '确认密码不能为空',
            'min_length': '密码长度至少为8位'
        }
    )
    mobile = forms.CharField(
        max_length=11,
        min_length=11,
        required=True,
        label='手机号',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入11位手机号'
        }),
        error_messages={
            'required': '手机号不能为空',
            'min_length': '手机号必须为11位',
            'max_length': '手机号必须为11位'
        }
    )

    def clean_username(self):
        """验证用户名非空和不重复"""
        username = self.cleaned_data.get('username')
        if not username or not username.strip():
            raise ValidationError('用户名不能为空')
        username = username.strip()
        if User.objects.filter(username=username).exists():
            raise ValidationError('该用户名已被使用，请选择其他用户名')
        return username

    def clean_password(self):
        """验证密码复杂度：至少8位，含大小写字母和数字"""
        password = self.cleaned_data.get('password')
        if not password:
            return password
        
        if len(password) < 8:
            raise ValidationError('密码长度至少为8位')
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not has_upper:
            raise ValidationError('密码必须包含至少一个大写字母')
        if not has_lower:
            raise ValidationError('密码必须包含至少一个小写字母')
        if not has_digit:
            raise ValidationError('密码必须包含至少一个数字')
        
        return password

    def clean_mobile(self):
        """验证手机号格式和唯一性"""
        mobile = self.cleaned_data.get('mobile')
        if not mobile:
            raise ValidationError('手机号不能为空')
        
        mobile = mobile.strip()
        
        # 验证是否为11位数字
        if not mobile.isdigit():
            raise ValidationError('手机号只能包含数字')
        
        if len(mobile) != 11:
            raise ValidationError('手机号必须为11位数字')
        
        # 验证手机号是否已注册
        if UserProfile.objects.filter(mobile=mobile).exists():
            raise ValidationError('该手机号已被注册，请使用其他手机号')
        
        return mobile

    def clean(self):
        """验证两次密码是否一致"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError({
                'password_confirm': '两次输入的密码不一致，请重新输入'
            })
        
        return cleaned_data


class LoginForm(forms.Form):
    """用户登录表单"""
    username = forms.CharField(
        max_length=150,
        label='用户名',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入用户名'
        })
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
    )


class GoodsForm(forms.ModelForm):
    """商品发布表单（基础版）"""
    class Meta:
        model = Goods
        fields = ['title', 'price', 'stock', 'category', 'desc', 'image']
        labels = {
            'title': '商品标题',
            'price': '商品价格',
            'stock': '库存数量',
            'category': '商品分类',
            'desc': '商品描述',
            'image': '商品图片',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入商品标题'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入商品价格',
                'step': '0.01',
                'min': '0'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入库存数量',
                'min': '1'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'desc': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '请输入商品描述',
                'rows': 5
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        error_messages = {
            'title': {
                'required': '商品标题不能为空',
            },
            'price': {
                'required': '商品价格不能为空',
            },
            'category': {
                'required': '请选择商品分类',
            },
            'stock': {
                'required': '请填写库存数量',
            },
            'desc': {
                'required': '商品描述不能为空',
            },
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 设置分类下拉框选项（下拉选已有的Category）
        self.fields['category'].queryset = Category.objects.all()
        # 设置必填字段
        self.fields['title'].required = True
        self.fields['price'].required = True
        self.fields['stock'].required = True
        self.fields['category'].required = True
        self.fields['desc'].required = True
        # 图片为可选
        self.fields['image'].required = False
    
    def clean_price(self):
        """验证价格必须大于0（基础验证）"""
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise ValidationError('商品价格必须大于0')
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None or stock <= 0:
            raise ValidationError('库存数量必须大于0')
        return stock
