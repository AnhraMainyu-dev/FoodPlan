from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Allergy,
    DietType,
    Dish,
    DishIngredient,
    Ingredient,
    MealType,
    Payment,
    PersonOption,
    PromoCode,
    Subscription,
    SubscriptionDuration,
    User,
    UserMenu,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "first_name", "is_staff", "is_active"]
    fieldsets = UserAdmin.fieldsets + (("Дополнительно", {"fields": ("avatar",)}),)


@admin.register(DietType)
class DietTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "index_value"]
    list_editable = ["price", "index_value"]


@admin.register(MealType)
class MealTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "index_value"]
    list_editable = ["price", "index_value"]


@admin.register(PersonOption)
class PersonOptionAdmin(admin.ModelAdmin):
    list_display = ["name", "count", "price", "index_value"]
    list_editable = ["count", "price", "index_value"]


@admin.register(SubscriptionDuration)
class SubscriptionDurationAdmin(admin.ModelAdmin):
    list_display = ["name", "months", "extra_percent", "index_value"]
    list_editable = ["months", "extra_percent", "index_value"]


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ["name", "index_value"]
    list_editable = ["index_value"]


class DishIngredientInline(admin.TabularInline):
    model = DishIngredient
    extra = 3
    autocomplete_fields = ["ingredient"]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "unit"]
    search_fields = ["name"]


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = [
        "get_image_preview",
        "title",
        "diet_type",
        "meal_type",
        "calories",
        "is_active",
    ]
    list_display_links = ["get_image_preview", "title"]
    list_filter = ["is_active", "diet_type", "meal_type", "allergies"]
    list_editable = ["is_active"]
    search_fields = ["title", "description"]
    filter_horizontal = ["allergies"]
    readonly_fields = ["get_image_preview"]
    inlines = [DishIngredientInline]

    @admin.display(description="Фото")
    def get_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 150px; '
                'border-radius: 6px; object-fit: cover;" />',
                obj.image.url,
            )
        return "Нет фото"


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_percent", "valid_until", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["is_active"]
    search_fields = ["code"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "diet_type",
        "persons",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["is_active", "diet_type", "persons"]
    search_fields = ["user__username", "user__email"]
    filter_horizontal = ["meal_types", "allergies"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "subscription",
        "duration",
        "promocode",
        "amount",
        "is_paid",
        "created_at",
    ]
    list_filter = ["is_paid", "duration", "created_at"]
    search_fields = ["subscription__user__username"]
    readonly_fields = ["created_at"]

    def changelist_view(self, request, extra_context=None):
        now = timezone.now()
        paid_qs = Payment.objects.filter(is_paid=True)

        month_revenue = (
            paid_qs.filter(
                created_at__year=now.year,
                created_at__month=now.month,
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        total_revenue = paid_qs.aggregate(total=Sum("amount"))["total"] or 0

        extra_context = extra_context or {}
        extra_context["title"] = (
            f"Оплаты | Выручка за текущий месяц: {month_revenue} руб. " f"(Всего: {total_revenue} руб.)"
        )
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(UserMenu)
class UserMenuAdmin(admin.ModelAdmin):
    list_display = [
        "subscription",
        "dish",
        "assigned_date",
        "replacements_left",
    ]
    list_filter = ["assigned_date"]
    search_fields = ["subscription__user__username", "dish__title"]
