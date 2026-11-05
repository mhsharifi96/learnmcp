from django.contrib import admin
from django.urls import include, path, re_path

from learn import oauth

admin.site.site_header = "learnmcp — instructor panel"
admin.site.site_title = "learnmcp"
admin.site.index_title = "Your classes"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("learn.api_urls")),
    # OAuth shim so clients that insist on OAuth (claude.ai) can add the connector.
    path(".well-known/oauth-authorization-server", oauth.authorization_server_metadata),
    re_path(r"^\.well-known/oauth-authorization-server/.*$", oauth.authorization_server_metadata),
    path(".well-known/openid-configuration", oauth.authorization_server_metadata),
    path(".well-known/oauth-protected-resource", oauth.protected_resource_metadata),
    re_path(r"^\.well-known/oauth-protected-resource/(?P<resource_path>.+)$", oauth.protected_resource_metadata),
    path("register", oauth.register),
    path("authorize", oauth.authorize),
    path("token", oauth.token),
    path("", include("learn.urls")),
]
