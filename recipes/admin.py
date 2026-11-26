from django.contrib import admin

from .models import DietType, MealType

admin.site.register([DietType, MealType])
