from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    avatar = models.ImageField("Аватар", upload_to="avatars/", blank=True)

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return self.username


class PlanOption(models.Model):
    name = models.CharField("Название", max_length=50)
    price = models.PositiveIntegerField("Цена", default=0)
    index_value = models.PositiveIntegerField("Номер с фронта", unique=True)

    class Meta:
        abstract = True
        ordering = ["index_value"]

    def __str__(self):
        return self.name


class DietType(PlanOption):
    class Meta(PlanOption.Meta):
        verbose_name = "тип меню"
        verbose_name_plural = "типы меню"


class MealType(PlanOption):
    class Meta(PlanOption.Meta):
        verbose_name = "приём пищи"
        verbose_name_plural = "приёмы пищи"


class PersonOption(PlanOption):
    count = models.PositiveIntegerField("Количество персон", default=1)

    class Meta(PlanOption.Meta):
        verbose_name = "количество персон"
        verbose_name_plural = "количества персон"


class SubscriptionDuration(models.Model):
    name = models.CharField("Название", max_length=50)
    months = models.PositiveIntegerField("Количество месяцев", default=1)
    extra_percent = models.PositiveIntegerField(
        "Наценка за срок (%)",
        default=0,
        help_text="0 для 1 мес., 60 для 3 мес., 80 для 6 мес., 100 для 12 мес.",
    )
    index_value = models.PositiveIntegerField("Номер с фронта", unique=True)

    class Meta:
        verbose_name = "срок подписки"
        verbose_name_plural = "сроки подписки"
        ordering = ["index_value"]

    def __str__(self):
        return self.name


class Allergy(models.Model):
    name = models.CharField("Название аллергии", max_length=50, unique=True)
    index_value = models.PositiveIntegerField("Номер с фронта", unique=True)

    class Meta:
        verbose_name = "аллергия"
        verbose_name_plural = "аллергии"
        ordering = ["index_value"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    diet_type = models.ForeignKey(
        DietType,
        verbose_name="Тип меню",
        on_delete=models.PROTECT,
    )
    persons = models.ForeignKey(
        PersonOption,
        verbose_name="Количество персон",
        on_delete=models.PROTECT,
    )
    meal_types = models.ManyToManyField(
        MealType,
        verbose_name="Приёмы пищи",
        related_name="subscriptions",
    )
    allergies = models.ManyToManyField(
        Allergy,
        verbose_name="Исключить аллергены",
        blank=True,
        related_name="subscriptions",
    )
    start_date = models.DateField("Дата начала", null=True, blank=True)
    end_date = models.DateField("Дата окончания", null=True, blank=True)
    is_active = models.BooleanField("Активна", default=False)

    class Meta:
        verbose_name = "подписка"
        verbose_name_plural = "подписки"
        ordering = ["-id"]

    def __str__(self):
        return f"Подписка #{self.id} ({self.user.username})"


class PromoCode(models.Model):
    code = models.CharField("Промокод", max_length=30, unique=True)
    discount_percent = models.PositiveIntegerField("Скидка (%)")
    valid_until = models.DateField("Действует до")
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "промокод"
        verbose_name_plural = "промокоды"

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}%)"


class Payment(models.Model):
    subscription = models.ForeignKey(
        Subscription,
        verbose_name="Подписка",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    duration = models.ForeignKey(
        SubscriptionDuration,
        verbose_name="Срок подписки",
        on_delete=models.PROTECT,
    )
    promocode = models.ForeignKey(
        PromoCode,
        verbose_name="Промокод",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    amount = models.PositiveIntegerField("Итоговая сумма")
    is_paid = models.BooleanField("Оплачено", default=False)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "оплата"
        verbose_name_plural = "оплаты"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Оплата #{self.id} на {self.amount} руб."

    def set_price(self):
        base_price = sum(
            meal.price for meal in self.subscription.meal_types.all()
        )
        price = base_price + (base_price * self.duration.extra_percent // 100)

        if self.promocode and self.promocode.is_active:
            price -= price * self.promocode.discount_percent // 100

        self.amount = price


class Ingredient(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    unit = models.CharField("Единица измерения", max_length=20)

    class Meta:
        verbose_name = "ингредиент"
        verbose_name_plural = "ингредиенты"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.unit})"


class Dish(models.Model):
    title = models.CharField("Название блюда", max_length=150)
    description = models.TextField("Рецепт и описание")
    image = models.ImageField("Фото блюда", upload_to="dishes/")
    diet_type = models.ForeignKey(
        DietType,
        verbose_name="Тип меню",
        on_delete=models.PROTECT,
        related_name="dishes",
    )
    meal_type = models.ForeignKey(
        MealType,
        verbose_name="Приём пищи",
        on_delete=models.PROTECT,
        related_name="dishes",
    )
    allergies = models.ManyToManyField(
        Allergy,
        verbose_name="Содержит аллергены",
        blank=True,
        related_name="dishes",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="DishIngredient",
        verbose_name="Ингредиенты",
        related_name="dishes",
    )
    calories = models.PositiveIntegerField("Калорийность (ккал)", default=0)
    is_active = models.BooleanField("Показывать в выдаче", default=True, db_index=True)

    class Meta:
        verbose_name = "блюдо"
        verbose_name_plural = "блюда"
        ordering = ["title"]

    def __str__(self):
        return self.title


class DishIngredient(models.Model):
    dish = models.ForeignKey(Dish, verbose_name="Блюдо", on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, verbose_name="Ингредиент", on_delete=models.CASCADE)
    amount = models.FloatField("Количество на 1 персону")

    class Meta:
        verbose_name = "ингредиент в блюде"
        verbose_name_plural = "ингредиенты в блюде"
        unique_together = ("dish", "ingredient")

    def __str__(self):
        return f"{self.ingredient.name} — {self.amount} {self.ingredient.unit}"


class UserMenu(models.Model):
    subscription = models.ForeignKey(
        Subscription,
        verbose_name="Подписка",
        on_delete=models.CASCADE,
        related_name="menus",
    )
    dish = models.ForeignKey(Dish, verbose_name="Блюдо", on_delete=models.CASCADE)
    assigned_date = models.DateField("Дата выдачи", auto_now_add=True)
    replacements_left = models.PositiveIntegerField("Осталось замен", default=3)

    class Meta:
        verbose_name = "меню пользователя"
        verbose_name_plural = "меню пользователей"
        ordering = ["-assigned_date"]

    def __str__(self):
        return f"{self.subscription} — {self.dish.title} ({self.assigned_date})"
