import random
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Allergy, DietType, Dish, MealType, PersonOption, Subscription, SubscriptionDuration, UserMenu

DIET_IMAGES = {
    0: "img/menu_classical.png",
    1: "img/menu_nizkougl.png",
    2: "img/menu_veg.png",
    3: "img/menu_keto.png",
}

DAILY_REPLACEMENTS_LIMIT = 3


def home(request):
    return render(request, "index.html")


def order(request):
    if request.method == "POST":
        messages.info(request, "Оформление заказа пока не подключено.")

    diets = [
        {
            "pk": diet.pk,
            "name": diet.name,
            "image": DIET_IMAGES.get(diet.index_value, "img/menu_classical.png"),
        }
        for diet in DietType.objects.order_by("index_value")
    ]
    context = {
        "diets": diets,
        "durations": SubscriptionDuration.objects.order_by("index_value"),
        "meals": MealType.objects.order_by("index_value"),
        "persons": PersonOption.objects.order_by("count"),
        "allergies": Allergy.objects.order_by("index_value"),
    }
    return render(request, "order.html", context)


def pick_dish(subscription, meal_type, exclude_dish_ids=None):
    exclude_dish_ids = exclude_dish_ids or []
    user_allergies = subscription.allergies.all()

    base_qs = (
        Dish.objects.filter(is_active=True, meal_type=meal_type)
        .exclude(allergies__in=user_allergies)
        .exclude(id__in=exclude_dish_ids)
        .distinct()
    )

    exact_dishes = list(base_qs.filter(diet_type=subscription.diet_type))
    if exact_dishes:
        return random.choice(exact_dishes)

    other_diet_dishes = list(base_qs)
    return random.choice(other_diet_dishes) if other_diet_dishes else None


@login_required
def subscription_menu(request, subscription_id):
    subscription = get_object_or_404(
        Subscription.objects.select_related("diet_type", "persons").prefetch_related("meal_types", "allergies"),
        id=subscription_id,
        user=request.user,
    )
    today = date.today()
    persons_count = subscription.persons.count

    existing_menus = {
        menu.dish.meal_type_id: menu
        for menu in UserMenu.objects.filter(
            subscription=subscription,
            assigned_date=today,
        ).select_related("dish", "dish__meal_type")
    }

    daily_cards = []
    spent_replacements = 0

    for meal_type in subscription.meal_types.all().order_by("index_value"):
        user_menu = existing_menus.get(meal_type.id)

        if not user_menu:
            dish = pick_dish(subscription, meal_type)
            if dish:
                user_menu = UserMenu.objects.create(
                    subscription=subscription,
                    dish=dish,
                    replacements_left=DAILY_REPLACEMENTS_LIMIT,
                )

        if user_menu:
            spent_replacements += DAILY_REPLACEMENTS_LIMIT - user_menu.replacements_left
            dish = user_menu.dish
            ingredients = []
            for item in dish.dishingredient_set.select_related("ingredient").all():
                total_amount = item.amount * persons_count
                if total_amount.is_integer():
                    total_amount = int(total_amount)
                ingredients.append(
                    {
                        "name": item.ingredient.name,
                        "amount": total_amount,
                        "unit": item.ingredient.unit,
                    }
                )

            daily_cards.append(
                {
                    "meal_name": meal_type.name,
                    "user_menu": user_menu,
                    "dish": dish,
                    "ingredients": ingredients,
                    "calories_per_portion": dish.calories,
                }
            )

    replacements_left = max(0, DAILY_REPLACEMENTS_LIMIT - spent_replacements)

    context = {
        "subscription": subscription,
        "daily_cards": daily_cards,
        "persons_count": persons_count,
        "replacements_left": replacements_left,
    }
    return render(request, "card3.html", context)


@login_required
def replace_dish(request, menu_id):
    user_menu = get_object_or_404(
        UserMenu.objects.select_related("subscription", "dish__meal_type"),
        id=menu_id,
        subscription__user=request.user,
    )
    today_menus = UserMenu.objects.filter(
        subscription=user_menu.subscription,
        assigned_date=user_menu.assigned_date,
    )
    spent_today = sum(DAILY_REPLACEMENTS_LIMIT - m.replacements_left for m in today_menus)
    replacements_left = max(0, DAILY_REPLACEMENTS_LIMIT - spent_today)

    if request.method == "POST" and replacements_left > 0:
        today_dish_ids = list(today_menus.values_list("dish_id", flat=True))
        new_dish = pick_dish(
            subscription=user_menu.subscription,
            meal_type=user_menu.dish.meal_type,
            exclude_dish_ids=today_dish_ids,
        )
        if new_dish:
            user_menu.dish = new_dish
            user_menu.replacements_left -= 1
            user_menu.save()

    return redirect("subscription_menu", subscription_id=user_menu.subscription.id)
