from typing import Optional, List, Dict, Any
from pydantic import Field
from asgiref.sync import sync_to_async
from mcp.server.mcpserver import MCPServer
from . import blog_operations

def register_tools(server: MCPServer):
    """Register all blog management tools on the MCPServer instance."""

    @server.tool()
    async def list_blog_posts(
        status: Optional[str] = Field(default="all", description="Filter by post status ('all', 'published', or 'draft'). Default is 'all'."),
        category: Optional[str] = Field(default=None, description="Optional category name or slug to filter (e.g. 'Technology', 'AI', 'AKTU-Guides', 'Trading')."),
        search: Optional[str] = Field(default=None, description="Keyword to search across title, content, excerpt, and tags."),
        time_filter: Optional[str] = Field(default=None, description="Quick time window filter ('today', 'yesterday', 'this_week', 'this_month', 'last_30_days', 'older')."),
        days_ago: Optional[int] = Field(default=None, description="Number of days to look back for updated posts (e.g. 7 for posts modified in last 7 days)."),
        sort_by: str = Field(default="updated_at", description="Sort field ('updated_at', 'publish_date', 'created_at', 'view_count', 'title'). Default is 'updated_at'."),
        order: str = Field(default="desc", description="Sort direction ('desc' for newest first, 'asc' for oldest first). Default is 'desc'."),
        limit: int = Field(default=15, description="Number of posts to return (1-50, default 15)."),
        offset: int = Field(default=0, description="Starting index for pagination (default 0).")
    ) -> Dict[str, Any]:
        """Scan, filter, and search GyanAangan blog posts by status, category, date, or keyword."""
        return await sync_to_async(blog_operations.list_posts)(
            status=status,
            category=category,
            search=search,
            time_filter=time_filter,
            days_ago=days_ago,
            sort_by=sort_by,
            order=order,
            limit=limit,
            offset=offset
        )

    @server.tool()
    async def get_blog_post(
        identifier: str = Field(description="The blog post ID (e.g. '55') or slug (e.g. 'aktu-btech-1st-year-syllabus-2026-27').")
    ) -> Dict[str, Any]:
        """Retrieve full details of a specific blog post including entire body content and SEO metadata."""
        post = await sync_to_async(blog_operations.get_post_by_id_or_slug)(identifier, include_content=True)
        if not post:
            return {"error": f"Blog post '{identifier}' not found."}
        return post

    @server.tool()
    async def create_blog_post(
        title: str = Field(description="The title of the blog post."),
        content: str = Field(
            description=(
                "The full content of the blog post. "
                "CRITICAL: Content MUST ALWAYS be provided in clean, semantic HTML format "
                "(e.g. using <p>, <h2>, <h3>, <ul>, <ol>, <li>, <blockquote>, <code>, <pre>, <strong>, <em>, <a>, <table>). "
                "NEVER provide raw markdown."
            )
        ),
        category: Optional[str] = Field(default=None, description="The category name or slug (e.g. 'Technology', 'Exams'). Auto-created if it does not exist."),
        tags: Optional[List[str]] = Field(default=None, description="List of tags for discovery (e.g. ['AKTU', 'Syllabus', 'BTech'])."),
        status: str = Field(default="draft", description="Initial status: 'draft' or 'published' (defaults to 'draft')."),
        excerpt: Optional[str] = Field(default=None, description="Short summary (max 500 chars). Auto-extracted from content if omitted."),
        meta_description: Optional[str] = Field(default=None, description="SEO meta description (max 160 chars)."),
        keywords: Optional[str] = Field(default=None, description="SEO keywords (comma-separated)."),
        is_featured: bool = Field(default=False, description="Whether this post is featured on the homepage."),
        featured_image_url: Optional[str] = Field(default=None, description="Optional public image URL (HTTP/HTTPS) or base64 data URI to download and set as the post's featured cover image."),
        author_email: Optional[str] = Field(default=None, description="Optional author email/username to assign as author. Defaults to DEFAULT_AUTHOR_EMAIL or primary superuser.")
    ) -> Dict[str, Any]:
        """Create a new blog post on GyanAangan.

        IMPORTANT FORMATTING RULE FOR CONTENT:
        The 'content' field MUST ALWAYS be provided in clean, semantic HTML format (e.g. using <p>, <h2>, <h3>, <ul>, <ol>, <li>, <blockquote>, <code>, <pre>, <strong>, <em>, <a>, <table>).
        Do NOT output raw, plain Markdown syntax (#, **, -) in 'content'. Always use valid HTML tags.
        """
        try:
            return await sync_to_async(blog_operations.create_post)(
                title=title,
                content=content,
                category=category,
                tags=tags,
                status=status,
                excerpt=excerpt,
                meta_description=meta_description,
                keywords=keywords,
                is_featured=is_featured,
                featured_image_url=featured_image_url,
                author_email=author_email
            )
        except Exception as e:
            return {"error": f"Failed to create blog post: {str(e)}"}

    @server.tool()
    async def update_blog_post(
        identifier: str = Field(description="The blog post ID or slug to update."),
        title: Optional[str] = Field(default=None, description="New title (optional)."),
        content: Optional[str] = Field(
            default=None,
            description=(
                "New full content for the post. "
                "CRITICAL: Content MUST ALWAYS be formatted in clean, semantic HTML format "
                "(<p>, <h2>, <h3>, <ul>, <li>, <code>, etc.). NEVER provide raw markdown."
            )
        ),
        category: Optional[str] = Field(default=None, description="New category name or slug (optional)."),
        tags: Optional[List[str]] = Field(default=None, description="New list of tags (optional)."),
        status: Optional[str] = Field(default=None, description="Change status to 'draft' or 'published' (optional)."),
        excerpt: Optional[str] = Field(default=None, description="New short excerpt (optional)."),
        meta_description: Optional[str] = Field(default=None, description="New SEO meta description (optional)."),
        keywords: Optional[str] = Field(default=None, description="New SEO keywords (optional)."),
        is_featured: Optional[bool] = Field(default=None, description="Toggle featured status (optional)."),
        featured_image_url: Optional[str] = Field(default=None, description="Optional new public image URL or base64 data URI to set as featured cover image (or 'remove' to delete).")
    ) -> Dict[str, Any]:
        """Update any fields of an existing blog post on GyanAangan.

        IMPORTANT FORMATTING RULE FOR CONTENT:
        If 'content' is provided, it MUST ALWAYS be formatted in clean, semantic HTML (<p>, <h2>, <h3>, <ul>, <li>, <code>, etc.).
        Do NOT output raw markdown.
        """
        try:
            res = await sync_to_async(blog_operations.update_post)(
                identifier=identifier,
                title=title,
                content=content,
                category=category,
                tags=tags,
                status=status,
                excerpt=excerpt,
                meta_description=meta_description,
                keywords=keywords,
                is_featured=is_featured,
                featured_image_url=featured_image_url
            )
            if not res:
                return {"error": f"Blog post '{identifier}' not found."}
            return res
        except Exception as e:
            return {"error": f"Failed to update blog post: {str(e)}"}

    @server.tool()
    async def set_featured_image(
        identifier: str = Field(description="The blog post ID (e.g. '55') or slug."),
        image_url: str = Field(description="Public image URL (HTTP/HTTPS) or base64 data URI (e.g. 'data:image/jpeg;base64,...'). To remove an existing featured image, pass 'remove' or 'none'.")
    ) -> Dict[str, Any]:
        """Set, update, or remove the featured cover image for a blog post.

        Accepts a public web URL or base64 data URI, downloads/decodes the image, and sets it as the post's featured cover image.
        """
        try:
            res = await sync_to_async(blog_operations.set_featured_image)(identifier, image_url)
            if not res:
                return {"error": f"Blog post '{identifier}' not found."}
            return res
        except Exception as e:
            return {"error": f"Failed to set featured image: {str(e)}"}

    @server.tool()
    async def append_to_blog_post(
        identifier: str = Field(description="The blog post ID or slug."),
        content_to_append: str = Field(
            description=(
                "The new HTML section/content to append to the end of the post. "
                "CRITICAL: Content MUST ALWAYS be in valid HTML format (e.g. <p>...</p>, <ul>...</ul>). "
                "Do NOT pass raw markdown."
            )
        ),
        heading: Optional[str] = Field(default=None, description="Optional H2 heading text for the new section (e.g. '2026 Update', 'Key Takeaways').")
    ) -> Dict[str, Any]:
        """Append an update, note, or new section to an existing blog post without rewriting its body.

        IMPORTANT FORMATTING RULE FOR CONTENT:
        'content_to_append' MUST ALWAYS be provided in valid HTML format (<p>...</p>, <ul>...</ul>, <blockquote>...</blockquote>).
        """
        try:
            res = await sync_to_async(blog_operations.append_to_post)(
                identifier=identifier,
                content_to_append=content_to_append,
                heading=heading
            )
            if not res:
                return {"error": f"Blog post '{identifier}' not found."}
            return res
        except Exception as e:
            return {"error": f"Failed to append to blog post: {str(e)}"}

    @server.tool()
    async def publish_blog_post(identifier: str) -> Dict[str, Any]:
        """Instantly publish a draft blog post on GyanAangan.

        Args:
            identifier: The blog post ID or slug to publish.

        Returns:
            The published blog post with live status and publication timestamp.
        """
        try:
            res = await sync_to_async(blog_operations.publish_post)(identifier)
            if not res:
                return {"error": f"Blog post '{identifier}' not found."}
            return res
        except Exception as e:
            return {"error": f"Failed to publish blog post: {str(e)}"}

    @server.tool()
    async def revert_to_draft(identifier: str) -> Dict[str, Any]:
        """Revert a published blog post back to draft status.

        Args:
            identifier: The blog post ID or slug to unpublish.

        Returns:
            The updated blog post with draft status.
        """
        try:
            res = await sync_to_async(blog_operations.revert_to_draft)(identifier)
            if not res:
                return {"error": f"Blog post '{identifier}' not found."}
            return res
        except Exception as e:
            return {"error": f"Failed to revert post to draft: {str(e)}"}

    @server.tool()
    async def delete_blog_post(identifier: str, confirm: bool = False) -> Dict[str, Any]:
        """Safely delete a blog post from GyanAangan.

        Args:
            identifier: The blog post ID or slug to delete.
            confirm: Must be explicitly True to prevent accidental deletion.

        Returns:
            Confirmation of deletion.
        """
        if not confirm:
            return {"error": "Deletion aborted. Set 'confirm=True' to confirm deletion of this post."}

        try:
            success = await sync_to_async(blog_operations.delete_post)(identifier)
            if not success:
                return {"error": f"Blog post '{identifier}' not found."}
            return {"status": "success", "message": f"Blog post '{identifier}' was successfully deleted."}
        except Exception as e:
            return {"error": f"Failed to delete blog post: {str(e)}"}

    @server.tool()
    async def list_categories() -> Dict[str, Any]:
        """List all available blog categories and their post counts on GyanAangan.

        Returns:
            A dictionary containing total_categories and the list of categories with name, slug, and post count.
        """
        return await sync_to_async(blog_operations.list_categories)()

    @server.tool()
    async def create_category(name: str) -> Dict[str, Any]:
        """Create a new blog category on GyanAangan.

        Args:
            name: The display name of the category (e.g. 'System Design').

        Returns:
            The created category details.
        """
        try:
            return await sync_to_async(blog_operations.create_category)(name)
        except Exception as e:
            return {"error": f"Failed to create category: {str(e)}"}

    @server.tool()
    async def get_blog_stats() -> Dict[str, Any]:
        """Get high-level summary metrics of all GyanAangan blogs (total, published, drafts, top categories).

        Returns:
            Overview statistics for rapid scanning and status assessment.
        """
        return await sync_to_async(blog_operations.get_blog_stats)()
