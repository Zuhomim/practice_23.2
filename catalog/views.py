from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.forms import inlineformset_factory
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse_lazy, reverse
from django.views.generic import DetailView, ListView, CreateView, UpdateView

from catalog.forms import ProductForm, VersionForm, ProductFormModerator
from catalog.models import Category, Product, Version
from catalog.services import get_cached_categories


class CategoryListView(ListView):
    model = Category
    extra_context = {
        'object_list': get_cached_categories(),
        'title': 'Категории'
    }


class ProductListView(ListView):
    model = Product
    template_name = 'product/product_list.html'

    def get_queryset(self):

        return super().get_queryset().filter(
            category=self.kwargs.get('pk'),
            owner=self.request.user
        )

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(**kwargs)
        for product in context_data['object_list']:
            active_version = product.version_set.filter(is_current=True).first()
            if active_version:
                product.active_version_number = active_version.number
                product.active_version_name = active_version.name
            else:
                product.active_version_number = None
                product.active_version_name = None
        return context_data


class ProductDetailView(DetailView):
    model = Product
    template_name = 'product/product_detail.html'


def contacts(request):
    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        message = request.POST.get('message')
        print(f'{name} ({phone}): {message}')
    return render(request, 'contacts/contact_list.html')


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    success_url = reverse_lazy('catalog:catalog')

    def form_valid(self, form):
        self.object = form.save()
        self.object.owner = self.request.user
        self.object.save()

        return super().form_valid(form)


class ProductUpdateView(PermissionRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    form_class = ProductForm
    permission_required = 'catalog.change_product'

    def get_success_url(self):
        return reverse('catalog:product_update', args=[self.kwargs.get('pk')])

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)

        VersionFormset = inlineformset_factory(Product, Version, form=VersionForm, extra=1)
        if self.request.method == 'POST':
            formset = VersionFormset(self.request.POST, instance=self.object)
        else:
            formset = VersionFormset(instance=self.object)

        context_data['formset'] = formset
        return context_data

    def form_valid(self, form):
        context_data = self.get_context_data()
        formset = context_data['formset']
        self.object = form.save()

        if formset.is_valid():
            formset.instance = self.object
            formset.save()
        return super().form_valid(form)

    def get_form_class(self):
        if self.request.user.groups.filter(name='Модератор').exists():
            return ProductFormModerator
        else:
            return ProductForm

    def test_func(self):
        _user = self.request.user
        _instance: Product = self.get_object()
        custom_perms: tuple = (
            'catalog.set_is_published',
            'catalog.set_category',
            'catalog.set_description',
        )

        if _user == _instance.owner:
            return True
        elif _user.groups.filter(name='Модератор') and _user.has_perms(custom_perms):
            return True
        return self.handle_no_permission()

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.object.owner != self.request.user and not self.request.user.is_staff:
            raise Http404("Вы не являетесь владельцем этого товара")
        return self.object


# FBV
# def catalog(request):
#     context = {
#         'object_list': Category.objects.all(),
#         'title': "TestStore",
#     }
#     return render(request, 'catalog/category_list.html', context)

# def product_info(request, pk):
#     product_item = Product.objects.get(pk=pk)
#     context = {
#         "object_item": product_item,
#         "title": f'Product {product_item.name}',
#     }
#     print(context["object_item"], product_item.name)
#     return render(request, 'product/product_detail.html', context)

# def product(request, pk):
#     category_item = Category.objects.get(pk=pk)
#     context = {
#         'object_list': Product.objects.filter(category_id=pk),
#         'title': f'Products from {category_item.name}',
#     }
#     return render(request, 'product/product_list.html', context)
