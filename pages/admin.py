from django.contrib import admin
from .models import Book, Category, Library, Loan, Order


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "price", "rating", "status")
    list_filter = ("category", "status")
    search_fields = ("title", "author", "category__name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "address", "phone")
    search_fields = ("name", "city", "address")
    list_filter = ("city",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "book",
        "quantity",
        "total_price",
        "status",
        "payment_status",
        "created_at",
    )
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("customer__username", "customer__email", "book__title")
    list_editable = ("status", "payment_status")
    readonly_fields = ("customer", "book", "quantity", "unit_price", "created_at")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "book", "status", "requested_at", "due_date")
    list_filter = ("status", "requested_at", "due_date")
    search_fields = ("customer__username", "customer__email", "book__title")
    readonly_fields = ("customer", "book", "status", "requested_at", "due_date")
