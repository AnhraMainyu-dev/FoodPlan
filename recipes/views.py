import random
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import OrderForm
from .models import (
    Allergy,
    DietType,
    Dish,
    MealType,
    Payment,
    PersonOption,
    Subscription,
    SubscriptionDuration,
    UserMenu,
)

DIET_IMAGES = {
    0: "img/menu_classical.png",
    1: "img/menu_nizkougl.png",
    2: "img/menu_veg.png",
    3: "img/menu_keto.png",
}

DAILY_REPLACEMENTS_LIMIT = 3


def home(request):
    return render(request, "index.html")


def save_order(user, data, payment):
    subscription = Subscription.objects.create(
        user=user,
        diet_type=data["diet_type"],
        persons=data["persons"],
    )

    try:
        subscription.meal_types.set(data["meal_types"])
        subscription.allergies.set(data["allergies"])
        payment.subscription = subscription
        payment.save()
    except DatabaseError:
        subscription.delete()
        raise


def order(request):
    if request.method != "POST":
        return render_order(request)

    post = request.POST.copy()
    post.setlist("meal_types", [value for value in post.getlist("meal_types") if value])
    form = OrderForm(post)

    if not form.is_valid():
        return render_order(request, form)

    data = form.cleaned_data
    payment = Payment(duration=data["duration"], promocode=data["promocode"])
    payment.set_price(data["meal_types"])

    if post.get("action") != "order":
        return render_order(request, form, payment.amount, payment.promocode)

    if not request.user.is_authenticated:
        form.add_error(None, "Войдите в аккаунт, чтобы оформить подписку.")
        return render_order(request, form, payment.amount, payment.promocode)

    save_order(request.user, data, payment)
    messages.success(request, "Оплата подтверждена.")
    return redirect(reverse("account") + "?tab=menu")


def render_order(request, form=None, price=None, promocode=None):
    meals = MealType.objects.all()
    if form is None:
        duration = SubscriptionDuration.objects.first()
        form = OrderForm(
            initial={
                "diet_type": DietType.objects.first(),
                "duration": duration,
                "meal_types": meals,
                "persons": PersonOption.objects.order_by("count").first(),
            }
        )
        if duration and meals:
            payment = Payment(duration=duration)
            payment.set_price(meals)
            price = payment.amount

    selected_diet = str(form["diet_type"].value())
    diets = [
        {
            "pk": diet.pk,
            "name": diet.name,
            "image": DIET_IMAGES.get(diet.index_value, "img/menu_classical.png"),
            "selected": str(diet.pk) == selected_diet,
        }
        for diet in DietType.objects.order_by("index_value")
    ]
    context = {
        "diets": diets,
        "form": form,
        "price": price,
        "promocode": promocode,
        "meals": meals,
        "selected_meals": [str(meal) for meal in form["meal_types"].value() or []],
        "allergies": Allergy.objects.all(),
        "selected_allergies": request.POST.getlist("allergies"),
    }
    return render(request, "order.html", context)


def get_available_dishes(subscription, meal_type, exclude_dish_ids=None):
    exclude_dish_ids = exclude_dish_ids or []
    user_allergies = subscription.allergies.all()

    base_qs = (
        Dish.objects.filter(is_active=True, meal_type=meal_type)
        .exclude(allergies__in=user_allergies)
        .exclude(id__in=exclude_dish_ids)
        .distinct()
    )

    exact_dishes = list(base_qs.filter(diet_type=subscription.diet_type))
    return exact_dishes or list(base_qs)


@login_required
def subscription_menu(request, subscription_id):
    subscription = get_object_or_404(
        Subscription.objects.select_related("diet_type", "persons").prefetch_related("meal_types", "allergies"),
        id=subscription_id,
        user=request.user,
    )
    today = date.today()
    persons_count = subscription.persons.count
    session_key = f"shown_dishes_{subscription.id}_{today}"
    shown_ids = set(request.session.get(session_key, []))

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
            dishes = get_available_dishes(subscription, meal_type, exclude_dish_ids=shown_ids)
            dish = random.choice(dishes) if dishes else None
            if dish:
                user_menu = UserMenu.objects.create(
                    subscription=subscription,
                    dish=dish,
                    replacements_left=DAILY_REPLACEMENTS_LIMIT,
                )

        if user_menu:
            shown_ids.add(user_menu.dish.id)
            spent_replacements += DAILY_REPLACEMENTS_LIMIT - user_menu.replacements_left
            dish = user_menu.dish

            alternatives = get_available_dishes(
                subscription,
                meal_type,
                exclude_dish_ids=shown_ids,
            )

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
                    "can_replace": bool(alternatives),
                }
            )

    request.session[session_key] = list(shown_ids)
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
        session_key = f"shown_dishes_{user_menu.subscription.id}_{user_menu.assigned_date}"
        shown_ids = set(
            request.session.get(
                session_key,
            )
        )
        shown_ids.update(today_menus.values_list("dish_id", flat=True))

        available_dishes = get_available_dishes(
            subscription=user_menu.subscription,
            meal_type=user_menu.dish.meal_type,
            exclude_dish_ids=shown_ids,
        )
        new_dish = random.choice(available_dishes) if available_dishes else None

        if new_dish:
            user_menu.dish = new_dish
            user_menu.replacements_left -= 1
            user_menu.save()
            shown_ids.add(new_dish.id)
            request.session[session_key] = list(shown_ids)

    return redirect("subscription_menu", subscription_id=user_menu.subscription.id)
