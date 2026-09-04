import os
import base64
import requests
from datetime import timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Q, Count
from django.core.files.base import ContentFile
from blog.models import BlogPost, Category
from django.contrib.auth.models import User

DEFAULT_AUTHOR_EMAIL = os.getenv("DEFAULT_AUTHOR_EMAIL", "")
FRONTEND_BLOG_URL = os.getenv("FRONTEND_BLOG_URL", "https://gyanaangan.in/blog")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.gyanaangan.in").rstrip("/")

def get_default_author(author_email: Optional[str] = None):
    """Find the author user for blog posts."""
    email_to_check = author_email or DEFAULT_AUTHOR_EMAIL
    if email_to_check:
        user = User.objects.filter(email__iexact=email_to_check).first()
        if not user:
            user = User.objects.filter(username__iexact=email_to_check).first()
        if user:
            return user

    # Automatically fallback to the first active superuser or staff member
    user = User.objects.filter(is_superuser=True, is_active=True).first()
    if not user:
        user = User.objects.filter(is_staff=True, is_active=True).first()
    if not user:
        user = User.objects.filter(is_active=True).first()
    if not user:
        raise ValueError("No active user found to assign as blog author.")
    return user

def serialize_post(post: BlogPost, include_content: bool = False) -> Dict[str, Any]:
    excerpt = post.excerpt or ""
    if len(excerpt) > 220 and not include_content:
        excerpt = excerpt[:217] + "..."

    featured_image_url = None
    if post.featured_image:
        try:
            url = post.featured_image.url
            if url.startswith("http://") or url.startswith("https://"):
                featured_image_url = url
            else:
                featured_image_url = f"{API_BASE_URL}{url}"
        except Exception:
            featured_image_url = None

    data = {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "status": post.status,
        "category": post.category.name if post.category else None,
        "category_slug": post.category.slug if post.category else None,
        "author": post.author.get_full_name() or post.author.username,
        "publish_date": post.publish_date.strftime("%Y-%m-%d %H:%M") if post.publish_date else None,
        "updated_at": post.updated_at.strftime("%Y-%m-%d %H:%M") if hasattr(post, "updated_at") and post.updated_at else None,
        "created_at": post.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(post, "created_at") and post.created_at else None,
        "reading_time_minutes": post.reading_time,
        "view_count": getattr(post, "view_count", 0),
        "is_featured": post.is_featured,
        "featured_image": featured_image_url,
        "excerpt": excerpt,
        "tags": list(post.tags.names()),
        "url": f"{FRONTEND_BLOG_URL}/{post.slug}" if post.slug else None,
    }

    if include_content:
        data["content"] = post.content
        data["word_count"] = len(post.content.split()) if post.content else 0
        data["meta_description"] = post.meta_description
        data["keywords"] = post.keywords

    return data

def save_featured_image(post: BlogPost, image_source: str) -> Optional[str]:
    """
    Downloads or decodes an image and sets it as the post's featured_image.
    Accepts:
      - HTTP/HTTPS URL
      - Base64 data URI (e.g. data:image/png;base64,...)
    Returns the URL of the saved image.
    """
    if not image_source or not image_source.strip():
        return None

    src = image_source.strip()
    image_bytes = None
    ext = ".jpg"

    if src.startswith("data:image/"):
        try:
            header, b64data = src.split(",", 1)
            if "image/png" in header:
                ext = ".png"
            elif "image/webp" in header:
                ext = ".webp"
            elif "image/gif" in header:
                ext = ".gif"
            elif "image/jpeg" in header or "image/jpg" in header:
                ext = ".jpg"
            image_bytes = base64.b64decode(b64data)
        except Exception as e:
            raise ValueError(f"Invalid base64 image data: {str(e)}")
    elif src.startswith("http://") or src.startswith("https://"):
        try:
            resp = requests.get(
                src,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "").lower()
            if "image/png" in content_type:
                ext = ".png"
            elif "image/webp" in content_type:
                ext = ".webp"
            elif "image/gif" in content_type:
                ext = ".gif"
            elif "image/jpeg" in content_type or "image/jpg" in content_type:
                ext = ".jpg"
            else:
                parsed = urlparse(src)
                path_ext = os.path.splitext(parsed.path)[1].lower()
                if path_ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    ext = path_ext if path_ext != ".jpeg" else ".jpg"

            image_bytes = resp.content
        except Exception as e:
            raise ValueError(f"Failed to download image from URL '{src}': {str(e)}")
    else:
        raise ValueError("Invalid image source. Must be a valid HTTP/HTTPS URL or base64 data URI.")

    if not image_bytes:
        raise ValueError("Image content is empty.")

    if len(image_bytes) > 15 * 1024 * 1024:
        raise ValueError("Image exceeds maximum allowed size of 15MB.")

    if post.featured_image:
        try:
            post.featured_image.delete(save=False)
        except Exception:
            pass

    slug_clean = post.slug or slugify(post.title) or "post"
    filename = f"{slug_clean}-featured-{int(timezone.now().timestamp())}{ext}"
    post.featured_image.save(filename, ContentFile(image_bytes), save=True)

    try:
        url = post.featured_image.url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{API_BASE_URL}{url}"
    except Exception:
        return None

def list_posts(
    status: Optional[str] = "all",
    category: Optional[str] = None,
    search: Optional[str] = None,
    time_filter: Optional[str] = None,
    days_ago: Optional[int] = None,
    sort_by: str = "updated_at",
    order: str = "desc",
    limit: int = 15,
    offset: int = 0
) -> Dict[str, Any]:
    """Scan and list posts with powerful multi-criteria filtering."""
    qs = BlogPost.objects.all()
    total_in_db = qs.count()

    # 1. Status Filter
    if status and status.lower() in ["draft", "published"]:
        qs = qs.filter(status=status.lower())

    # 2. Category Filter
    if category:
        qs = qs.filter(Q(category__slug__iexact=category) | Q(category__name__iexact=category))

    # 3. Search Filter
    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search) |
            Q(excerpt__icontains=search) |
            Q(tags__name__icontains=search)
        ).distinct()

    # 4. Time Filters
    now = timezone.now()
    if time_filter:
        tf = time_filter.lower().strip()
        if tf == "today":
            qs = qs.filter(updated_at__date=now.date())
        elif tf == "yesterday":
            yesterday = now.date() - timedelta(days=1)
            qs = qs.filter(updated_at__date=yesterday)
        elif tf == "this_week":
            start_week = now - timedelta(days=now.weekday())
            qs = qs.filter(updated_at__gte=start_week)
        elif tf == "this_month":
            qs = qs.filter(updated_at__year=now.year, updated_at__month=now.month)
        elif tf == "last_30_days":
            qs = qs.filter(updated_at__gte=now - timedelta(days=30))
        elif tf == "older":
            qs = qs.filter(updated_at__lt=now - timedelta(days=30))

    if days_ago is not None and days_ago > 0:
        since_date = now - timedelta(days=days_ago)
        qs = qs.filter(updated_at__gte=since_date)

    # 5. Sorting
    sort_fields = {
        "updated_at": "updated_at",
        "publish_date": "publish_date",
        "created_at": "created_at",
        "view_count": "view_count",
        "title": "title",
    }
    field = sort_fields.get(sort_by, "updated_at")
    prefix = "-" if order.lower() == "desc" else ""
    qs = qs.order_by(f"{prefix}{field}")

    total_matching = qs.count()
    limit = min(max(1, limit), 50)
    offset = max(0, offset)
    posts = qs[offset:offset + limit]

    return {
        "total_matching_posts": total_matching,
        "total_in_database": total_in_db,
        "offset": offset,
        "limit": limit,
        "returned_count": len(posts),
        "posts": [serialize_post(p, include_content=False) for p in posts]
    }

def get_post_by_id_or_slug(identifier: str, include_content: bool = True) -> Optional[Dict[str, Any]]:
    post = None
    if identifier.isdigit():
        post = BlogPost.objects.filter(id=int(identifier)).first()
    if not post:
        post = BlogPost.objects.filter(slug=identifier).first()
    if not post:
        post = BlogPost.objects.filter(title__iexact=identifier).first()

    if not post:
        return None
    return serialize_post(post, include_content=include_content)

def create_post(
    title: str,
    content: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: str = "draft",
    excerpt: Optional[str] = None,
    meta_description: Optional[str] = None,
    keywords: Optional[str] = None,
    is_featured: bool = False,
    featured_image_url: Optional[str] = None,
    author_email: Optional[str] = None,
) -> Dict[str, Any]:
    author = get_default_author(author_email)

    category_obj = None
    if category:
        category_obj = Category.objects.filter(slug=slugify(category)).first()
        if not category_obj:
            category_obj = Category.objects.filter(name__iexact=category).first()
        if not category_obj:
            category_obj = Category.objects.create(name=category.strip(), slug=slugify(category))

    if not excerpt:
        clean_text = " ".join(content.replace("<p>", " ").replace("</p>", " ").replace("<br>", " ").split())
        excerpt = clean_text[:250] + "..." if len(clean_text) > 250 else clean_text

    slug = slugify(title)
    base_slug = slug
    counter = 1
    while BlogPost.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    post_status = "published" if status.lower() == "published" else "draft"
    publish_date = timezone.now() if post_status == "published" else None

    post = BlogPost.objects.create(
        title=title,
        slug=slug,
        author=author,
        category=category_obj,
        content=content,
        excerpt=excerpt,
        status=post_status,
        publish_date=publish_date,
        meta_description=meta_description or excerpt[:155],
        keywords=keywords or "",
        is_featured=is_featured
    )

    if tags:
        clean_tags = [t.strip() for t in tags if t.strip()]
        if clean_tags:
            post.tags.set(clean_tags)

    if featured_image_url:
        save_featured_image(post, featured_image_url)

    post.save()
    return serialize_post(post, include_content=True)

def update_post(
    identifier: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    excerpt: Optional[str] = None,
    meta_description: Optional[str] = None,
    keywords: Optional[str] = None,
    is_featured: Optional[bool] = None,
    featured_image_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    post = None
    if identifier.isdigit():
        post = BlogPost.objects.filter(id=int(identifier)).first()
    if not post:
        post = BlogPost.objects.filter(slug=identifier).first()
    if not post:
        return None

    if title is not None:
        post.title = title
    if content is not None:
        post.content = content
    if excerpt is not None:
        post.excerpt = excerpt
    if meta_description is not None:
        post.meta_description = meta_description
    if keywords is not None:
        post.keywords = keywords
    if is_featured is not None:
        post.is_featured = is_featured

    if status is not None:
        new_status = "published" if status.lower() == "published" else "draft"
        if new_status == "published" and post.status != "published":
            if not post.publish_date:
                post.publish_date = timezone.now()
        post.status = new_status

    if category is not None:
        if category.strip() == "":
            post.category = None
        else:
            cat_obj = Category.objects.filter(slug=slugify(category)).first()
            if not cat_obj:
                cat_obj = Category.objects.filter(name__iexact=category).first()
            if not cat_obj:
                cat_obj = Category.objects.create(name=category.strip(), slug=slugify(category))
            post.category = cat_obj

    if tags is not None:
        clean_tags = [t.strip() for t in tags if t.strip()]
        post.tags.set(clean_tags)

    if featured_image_url is not None:
        clean_img = featured_image_url.strip().lower()
        if clean_img in ["", "none", "remove", "delete", "clear"]:
            if post.featured_image:
                post.featured_image.delete(save=False)
                post.featured_image = None
        else:
            save_featured_image(post, featured_image_url)

    post.save()
    return serialize_post(post, include_content=True)

def set_featured_image(identifier: str, image_url: str) -> Optional[Dict[str, Any]]:
    """Set, replace, or clear the featured image for a specific blog post."""
    post = None
    if identifier.isdigit():
        post = BlogPost.objects.filter(id=int(identifier)).first()
    if not post:
        post = BlogPost.objects.filter(slug=identifier).first()
    if not post:
        return None

    clean_img = (image_url or "").strip().lower()
    if clean_img in ["", "none", "remove", "delete", "clear"]:
        if post.featured_image:
            post.featured_image.delete(save=False)
            post.featured_image = None
            post.save()
    else:
        save_featured_image(post, image_url)
        post.save()

    return serialize_post(post, include_content=True)

def append_to_post(
    identifier: str,
    content_to_append: str,
    heading: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Conveniently append content to a post without having to supply full body."""
    post = None
    if identifier.isdigit():
        post = BlogPost.objects.filter(id=int(identifier)).first()
    if not post:
        post = BlogPost.objects.filter(slug=identifier).first()
    if not post:
        return None

    addition = ""
    if heading:
        addition += f"\n\n<h2>{heading}</h2>\n"
    addition += f"\n{content_to_append}\n"

    post.content = (post.content or "") + addition
    post.save()
    return serialize_post(post, include_content=True)

def publish_post(identifier: str) -> Optional[Dict[str, Any]]:
    post = None
    if identifier.isdigit():
        post = BlogPost.objects.filter(id=int(identifier)).first()
    if not post:
        post = BlogPost.objects.filter(slug=identifier).first()
    if not post:
        return None

    post.status = "published"
    if not post.publish_date:
        post.publish_date = timezone.now()
    post.save()
    return serialize_post(post, include_content=False)

def revert_to_draft(identifier: str) -> Optional[Dict[str, Any]]:
    post = None
    if identifier.isdigit():
        post = BlogPost.objects.filter(id=int(identifier)).first()
    if not post:
        post = BlogPost.objects.filter(slug=identifier).first()
    if not post:
        return None

    post.status = "draft"
    post.save()
    return serialize_post(post, include_content=False)

def delete_post(identifier: str) -> bool:
    post = None
    if identifier.isdigit():
        post = BlogPost.objects.filter(id=int(identifier)).first()
    if not post:
        post = BlogPost.objects.filter(slug=identifier).first()
    if not post:
        return False

    post.delete()
    return True

def list_categories() -> Dict[str, Any]:
    cats = Category.objects.annotate(post_count=Count("posts")).order_by("-post_count")
    return {
        "total_categories": cats.count(),
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "post_count": c.post_count
            }
            for c in cats
        ]
    }

def create_category(name: str) -> Dict[str, Any]:
    slug = slugify(name)
    cat, created = Category.objects.get_or_create(slug=slug, defaults={"name": name.strip()})
    return {
        "id": cat.id,
        "name": cat.name,
        "slug": cat.slug,
        "created": created
    }

def get_blog_stats() -> Dict[str, Any]:
    """Get high-level summary metrics of all blogs on GyanAangan."""
    total_posts = BlogPost.objects.count()
    published_count = BlogPost.objects.filter(status="published").count()
    draft_count = BlogPost.objects.filter(status="draft").count()
    featured_count = BlogPost.objects.filter(is_featured=True).count()
    categories_count = Category.objects.count()

    top_categories = Category.objects.annotate(post_count=Count("posts")).order_by("-post_count")[:5]

    return {
        "total_posts": total_posts,
        "published_posts": published_count,
        "draft_posts": draft_count,
        "featured_posts": featured_count,
        "categories_count": categories_count,
        "top_categories": [
            {"name": c.name, "slug": c.slug, "post_count": c.post_count}
            for c in top_categories
        ]
    }
