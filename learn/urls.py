from django.urls import path

from learn import views

app_name = "learn"

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz", views.healthz, name="healthz"),
    path("signup/", views.signup, name="signup"),
    path("join/", views.join_code, name="join_code"),
    path("join/<str:code>/", views.join, name="join"),
    path("connect/<int:enrollment_id>/", views.connect, name="connect"),
    path("me/", views.my_data, name="me"),
    path("me/restore/", views.restore, name="restore"),
    path("me/<int:enrollment_id>/regenerate/", views.regenerate, name="regenerate"),
    path("me/<int:enrollment_id>/leave/", views.leave, name="leave"),
    path("r/<str:key>", views.pack_submit, name="pack_submit"),
]
