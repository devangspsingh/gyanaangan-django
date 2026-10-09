import hashlib
import logging
from urllib.parse import urlencode
from django.core.cache import cache
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def get_cache_version(prefix: str) -> int:
    """
    Retrieves the current cache version for a specific entity prefix.
    If the version does not exist, it initializes it to 1.
    """
    version_key = f"cache_ver:{prefix}"
    try:
        v = cache.get(version_key)
        if v is None:
            cache.set(version_key, 1, timeout=None)
            v = 1
        return int(v)
    except Exception as e:
        logger.warning("Error getting cache version for %s: %s", prefix, e)
        return 1


def bump_cache_version(prefix: str) -> int:
    """
    Atomically increments the cache version in Redis for a specific entity prefix.
    Instantly invalidates all cached entries for this prefix.
    """
    version_key = f"cache_ver:{prefix}"
    try:
        new_v = cache.incr(version_key)
        logger.info("Bumped cache version for '%s' to %s", prefix, new_v)
        return new_v
    except Exception:
        try:
            cache.set(version_key, 2, timeout=None)
            logger.info("Initialized bumped cache version for '%s' to 2", prefix)
            return 2
        except Exception as e:
            logger.warning("Error bumping cache version for %s: %s", prefix, e)
            return 1


def build_unauthenticated_cache_key(
    prefix: str, action: str, request=None, identifier: str = None
) -> str:
    """
    Builds a deterministic, collision-free cache key for unauthenticated requests.
    Query parameters are sorted so parameter order does not affect the key.
    """
    if action == "detail" and identifier:
        return f"{prefix}:detail:{identifier}"

    # Handle list action with query parameters
    query_params = None
    if request:
        if hasattr(request, "query_params") and request.query_params:
            query_params = request.query_params
        elif hasattr(request, "GET") and request.GET:
            query_params = request.GET

    if query_params:
        items = sorted(query_params.lists())
        query_str = urlencode(items, doseq=True)
        query_hash = hashlib.md5(query_str.encode("utf-8")).hexdigest()
        return f"{prefix}:list:{query_hash}"

    return f"{prefix}:list:default"


class UnauthenticatedCacheMixin:
    """
    DRF ViewSet Mixin that caches responses strictly for unauthenticated users.
    Authenticated requests ALWAYS bypass the cache to guarantee fresh, personalized data.
    """

    cache_prefix = None
    cache_timeout = 1800  # 30 minutes default

    def get_cache_prefix(self):
        return (
            self.cache_prefix
            or self.__class__.__name__.lower().replace("viewset", "")
        )

    def list(self, request, *args, **kwargs):
        # STRICTLY skip cache for authenticated users
        if request.user and request.user.is_authenticated:
            return super().list(request, *args, **kwargs)

        prefix = self.get_cache_prefix()
        version = get_cache_version(prefix)
        cache_key = build_unauthenticated_cache_key(
            prefix=prefix, action="list", request=request
        )

        try:
            cached_data = cache.get(cache_key, version=version)
            if cached_data is not None:
                return Response(cached_data)
        except Exception as e:
            logger.warning("Cache read failed for key %s: %s", cache_key, e)

        response = super().list(request, *args, **kwargs)

        if response.status_code == 200:
            try:
                cache.set(
                    cache_key,
                    response.data,
                    timeout=self.cache_timeout,
                    version=version,
                )
            except Exception as e:
                logger.warning("Cache write failed for key %s: %s", cache_key, e)

        return response

    def retrieve(self, request, *args, **kwargs):
        # STRICTLY skip cache for authenticated users
        if request.user and request.user.is_authenticated:
            return super().retrieve(request, *args, **kwargs)

        prefix = self.get_cache_prefix()
        version = get_cache_version(prefix)

        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_val = (
            kwargs.get(lookup_url_kwarg)
            or kwargs.get("slug")
            or kwargs.get("pk")
        )

        cache_key = build_unauthenticated_cache_key(
            prefix=prefix, action="detail", identifier=str(lookup_val)
        )

        try:
            cached_data = cache.get(cache_key, version=version)
            if cached_data is not None:
                return Response(cached_data)
        except Exception as e:
            logger.warning("Cache read failed for key %s: %s", cache_key, e)

        response = super().retrieve(request, *args, **kwargs)

        if response.status_code == 200:
            try:
                cache.set(
                    cache_key,
                    response.data,
                    timeout=self.cache_timeout,
                    version=version,
                )
            except Exception as e:
                logger.warning("Cache write failed for key %s: %s", cache_key, e)

        return response
