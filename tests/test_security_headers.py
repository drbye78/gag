"""Tests for security headers."""

import pytest
from fastapi.testclient import TestClient

from api.main import app as main_app
from core.config import get_settings, reset_settings


class TestSecurityHeaders:
    """Test security headers middleware."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def test_csp_header_present(self):
        """CSP header should be present on all responses."""
        client = TestClient(main_app)
        response = client.get("/")
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp

    def test_x_content_type_options_header(self):
        """X-Content-Type-Options should be nosniff."""
        client = TestClient(main_app)
        response = client.get("/")
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_header(self):
        """X-Frame-Options should be DENY."""
        client = TestClient(main_app)
        response = client.get("/")
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_referrer_policy_header(self):
        """Referrer-Policy should be strict-origin-when-cross-origin."""
        client = TestClient(main_app)
        response = client.get("/")
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self):
        """Permissions-Policy should restrict sensitive features."""
        client = TestClient(main_app)
        response = client.get("/")
        assert "Permissions-Policy" in response.headers

    def test_hsts_header_not_present_by_default(self):
        """HSTS header should NOT be present when enable_hsts is False."""
        client = TestClient(main_app)
        response = client.get("/")
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_header_present_when_enabled(self):
        """HSTS header should be present when enable_hsts is True."""
        import os
        os.environ["ENABLE_HSTS"] = "true"
        reset_settings()

        from api.main import _cors_settings
        _cors_settings.enable_hsts = True

        client = TestClient(main_app)
        response = client.get("/")
        assert "Strict-Transport-Security" in response.headers
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

        del os.environ["ENABLE_HSTS"]
        reset_settings()
