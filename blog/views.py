from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from .models import BlogPost
from core.models import SEODetail
from django.templatetags.static import static


# View for displaying all blog posts
def blog_list(request):
    blogs = BlogPost.published.all()  # Fetch only published blogs
    context = {"blogs": blogs}
    seo_detail = SEODetail.objects.filter(page_name="blog").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Available Blogs - Gyan Aangan",
            meta_description="Explore a variety of blogs to enhance your knowledge at Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )
    context = {
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static("images/default-og-image.jpg")
        ),
        "site_name": seo_detail.site_name,
        "blogs": blogs,
    }
    return render(request, "blog/blog_list.html", context)


# View for displaying a single blog post
def blog_detail(request, slug):
    blog = get_object_or_404(BlogPost, slug=slug, status="published")

    # seo_detail = SEODetail.objects.filter(page_name=blog.title).first()
    # print(seo_detail)

    seo_detail = SEODetail(
        title=f"{blog.title} - Gyan Aangan",
        meta_description=f"{blog.meta_description} - {blog.excerpt}",
        og_image=None,
        site_name="Gyan Aangan",
    )
    print(seo_detail)
    
    # Check if the logged-in user is a superuser/admin and provide edit link
    is_admin = request.user.is_authenticated and request.user.is_superuser
    context = {
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            blog.og_image.url
            if blog.og_image
            else static("images/default-og-image.jpg")
        ),
        "site_name": seo_detail.site_name,
        "blog": blog,
        "is_admin":is_admin
    }

    return render(request, "blog/blog_detail.html", context)
