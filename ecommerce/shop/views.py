# shop/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Product, Category, Wishlist, Cart as CartModel, CartItem, Order
from .cart import Cart
from .forms import CartAddProductForm, OrderCreateForm


def home(request):
    products = Product.objects.filter(available=True).order_by('?')[:8]
    return render(request, 'shop/home.html', {'products': products})


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
    })


def product_detail(request, id, slug=None):  # 使slug可选
    product = get_object_or_404(Product, id=id, available=True)
    if slug and product.slug != slug:  # 验证slug是否匹配
        return redirect('shop:product_detail', id=id, slug=product.slug)
    cart_product_form = CartAddProductForm()
    return render(request, 'shop/product/detail.html', {  # 修正模板路径
        'product': product,
        'cart_product_form': cart_product_form,
    })
    # 在视图函数中临时添加调试代码
    print(template_exists('shop/detail.html'))  # 检查模板是否能被找到

def search(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            available=True
        )
    else:
        products = Product.objects.none()

    return render(request, 'shop/product/search.html', {
        'products': products,
        'query': query,
    })


@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'shop/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f"Added {product.name} To Wishlist")
    return redirect('shop:wishlist')


@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f"Removed from wishlist {product.name}")
    return redirect('shop:wishlist')


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product, quantity=cd['quantity'], override_quantity=cd['override'])

    return redirect('shop:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('shop:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(initial={
            'quantity': item['quantity'],
            'override': True
        })
    return render(request, 'shop/cart/detail.html', {'cart': cart})


@login_required
def checkout(request):
    cart = Cart(request)
    if not cart:
        return redirect('shop:home')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            # 创建购物车模型实例
            cart_model = CartModel.objects.create(user=request.user)

            # 添加购物车项
            for item in cart:
                CartItem.objects.create(
                    cart=cart_model,
                    product=item['product'],
                    quantity=item['quantity']
                )

            # 创建订单
            order = Order.objects.create(
                user=request.user,
                cart=cart_model,
                shipping_address=form.cleaned_data['shipping_address'],
                billing_address=form.cleaned_data.get('billing_address', ''),
                payment_method=form.cleaned_data['payment_method']
            )

            # 清空会话中的购物车
            cart.clear()

            messages.success(request, 'The order has been created successfully!')
            return render(request, 'shop/order/created.html', {'order': order})
    else:
        # 预填充用户地址
        initial_data = {
            'shipping_address': request.user.address,
            'payment_method': 'credit_card'
        }
        form = OrderCreateForm(initial=initial_data)

    return render(request, 'shop/order/checkout.html', {
        'cart': cart,
        'form': form,
    })


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'shop/order/history.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/order/detail.html', {'order': order})
