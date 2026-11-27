from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from recipes.views import home, order

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("order/", order, name="order"),
    path("login/", TemplateView.as_view(template_name="auth.html"), name="login"),
    path("register/", TemplateView.as_view(template_name="registration.html"), name="register"),
    path("account/", TemplateView.as_view(template_name="lk.html"), name="account"),
    path("dish/<int:pk>/", TemplateView.as_view(template_name="card3.html"), name="dish"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
