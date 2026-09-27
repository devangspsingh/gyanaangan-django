from django.urls import path
from django.shortcuts import redirect
from . import views


def blog_frontend_redirect(request, *args, **kwargs):
    path = request.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    qs = request.META.get("QUERY_STRING", "")
    target = f"https://gyanaangan.in{path}" + (f"?{qs}" if qs else "")
    return redirect(target, permanent=True)


urlpatterns = [
    path("", blog_frontend_redirect, name="blog_list"),
    path("<slug:slug>/", blog_frontend_redirect, name="blog_detail"),
]

