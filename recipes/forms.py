from django import forms
from django.utils import timezone

from .models import (
    Allergy,
    DietType,
    MealType,
    PersonOption,
    PromoCode,
    SubscriptionDuration,
)


class OrderForm(forms.Form):
    diet_type = forms.ModelChoiceField(DietType.objects.all())
    duration = forms.ModelChoiceField(SubscriptionDuration.objects.all())
    meal_types = forms.ModelMultipleChoiceField(MealType.objects.all())
    persons = forms.ModelChoiceField(PersonOption.objects.all())
    allergies = forms.ModelMultipleChoiceField(Allergy.objects.all(), required=False)
    promocode = forms.CharField(max_length=30, required=False)

    def clean_promocode(self):
        code = self.cleaned_data["promocode"].strip()
        if not code:
            return None

        try:
            return PromoCode.objects.get(
                code__iexact=code,
                is_active=True,
                valid_until__gte=timezone.localdate(),
            )
        except PromoCode.DoesNotExist:
            raise forms.ValidationError("Промокод недействителен")
