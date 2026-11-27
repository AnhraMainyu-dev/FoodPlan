from django.contrib import messages
from django.shortcuts import render

from .models import Allergy, DietType, MealType, PersonOption, SubscriptionDuration

DIET_IMAGES = {
    0: "img/menu_classical.png",
    1: "img/menu_nizkougl.png",
    2: "img/menu_veg.png",
    3: "img/menu_keto.png",
}


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
