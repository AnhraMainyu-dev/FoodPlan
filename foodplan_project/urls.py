from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.views.generic import TemplateView

from recipes.forms import LoginForm
from recipes.views import account, home, order, replace_dish, subscription_menu

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("order/", order, name="order"),
    path(
        "login/",
        LoginView.as_view(
            template_name="auth.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("register/", TemplateView.as_view(template_name="registration.html"), name="register"),
    path("account/", account, name="account"),
    path("dish/<int:pk>/", TemplateView.as_view(template_name="card3.html"), name="dish"),
    path("subscription/<int:subscription_id>/menu/", subscription_menu, name="subscription_menu"),
    path("menu/<int:menu_id>/replace/", replace_dish, name="replace_dish"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
