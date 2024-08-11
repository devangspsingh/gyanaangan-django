from django.shortcuts import render
from django.templatetags.static import static
from django.utils.timezone import now
from .models import SEODetail


def terms_and_conditions(request):
    seo_detail = SEODetail.objects.filter(page_name="terms_and_conditions").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Terms and Conditions - Gyan Aangan",
            meta_description="Read the terms and conditions for using the Gyan Aangan platform.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "last_updated": now().strftime("%B %d, %Y"),
        "site_url": "https://gyanaangan.dspsc.live",
        "contact_email": "dspscpy@gmail.com",
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static("images/default-og-image.jpg")
        ),
        "site_name": seo_detail.site_name,
    }
    return render(request, "core/terms_and_conditions.html", context)


def privacy_policy(request):
    seo_detail = SEODetail.objects.filter(page_name="privacy_policy").first()
    if not seo_detail:
        seo_detail = SEODetail(
            title="Privacy Policy - Gyan Aangan",
            meta_description="Understand how we collect, use, and protect your personal information on Gyan Aangan.",
            og_image=None,
            site_name="Gyan Aangan",
        )

    context = {
        "last_updated": now().strftime("%B %d, %Y"),
        "site_url": "https://gyanaangan.dspsc.live",
        "contact_email": "dspscpy@gmail.com",
        "title": seo_detail.title,
        "meta_description": seo_detail.meta_description,
        "og_image": (
            seo_detail.og_image.url
            if seo_detail.og_image
            else static("images/default-og-image.jpg")
        ),
        "site_name": seo_detail.site_name,
    }
    return render(request, "core/privacy_policy.html", context)
