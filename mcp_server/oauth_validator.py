import logging
from urllib.parse import urlsplit
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauth2_provider.models import AbstractApplication

logger = logging.getLogger(__name__)

TRUSTED_AI_DOMAINS = (
    "chatgpt.com",
    "claude.ai",
    "googleusercontent.com",
    "cloud.google.com",
)


class AIConnectOAuth2Validator(OAuth2Validator):
    """
    Tolerant OAuth 2.0 Validator for AI Assistants (ChatGPT, Google Gemini, Claude).
    Allows public PKCE clients to authenticate seamlessly even if ChatGPT or Gemini sends
    a dummy or custom client_secret, or uses PKCE with code_verifier.
    Also dynamically validates and auto-registers AI connector redirect URIs.
    """

    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        if request.client and request.client.redirect_uri_allowed(redirect_uri):
            return True

        parsed = urlsplit(redirect_uri)
        if any(parsed.netloc == d or parsed.netloc.endswith("." + d) for d in TRUSTED_AI_DOMAINS):
            if request.client:
                current = set(request.client.redirect_uris.split())
                if redirect_uri not in current:
                    request.client.redirect_uris = f"{request.client.redirect_uris} {redirect_uri}".strip()
                    request.client.save(update_fields=["redirect_uris"])
                    logger.info(f"Auto-registered redirect URI '{redirect_uri}' for application '{request.client.name}'.")
            return True
        return False

    def _authenticate_request_body(self, request):
        try:
            client_id = request.client_id
            client_secret = getattr(request, "client_secret", "") or ""
        except AttributeError:
            return False

        if self._load_application(client_id, request) is None:
            return False

        # Public clients using PKCE do not require secret verification
        if request.client.client_type == AbstractApplication.CLIENT_PUBLIC:
            return True
        # If client is confidential but request contains code_verifier (PKCE flow), allow
        if getattr(request, "code_verifier", None):
            return True
        elif not self._check_secret(client_secret, request.client.client_secret):
            return False
        else:
            return True

    def _authenticate_basic_auth(self, request):
        auth = self._extract_basic_auth(request)
        if not auth:
            return False
        client_id, client_secret = auth

        if self._load_application(client_id, request) is None:
            return False

        # Public clients using PKCE do not require secret verification
        if request.client.client_type == AbstractApplication.CLIENT_PUBLIC:
            return True
        # If client is confidential but request contains code_verifier (PKCE flow), allow
        if getattr(request, "code_verifier", None):
            return True
        elif not self._check_secret(client_secret, request.client.client_secret):
            return False
        else:
            return True
