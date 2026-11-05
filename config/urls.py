from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "learnmcp — instructor panel"
admin.site.site_title = "learnmcp"
admin.site.index_title = "Your classes"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("learn.urls")),
]
