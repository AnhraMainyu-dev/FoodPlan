from django.contrib import messages
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import OrderForm
from .models import Allergy, DietType, MealType, Payment, PersonOption, Subscription, SubscriptionDuration

DIET_IMAGES = {
    0: "img/menu_classical.png",
    1: "img/menu_nizkougl.png",
    2: "img/menu_veg.png",
    3: "img/menu_keto.png",
}


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
