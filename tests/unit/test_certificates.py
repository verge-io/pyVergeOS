"""Unit tests for Certificate operations."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.certificates import (
    CERT_TYPE_DISPLAY,
    CERT_TYPE_MAP,
    KEY_TYPE_DISPLAY,
    KEY_TYPE_MAP,
    Certificate,
)

# =============================================================================
# Certificate Model Tests
# =============================================================================


class TestCertificate:
    """Unit tests for Certificate model."""

    def test_certificate_properties(self, mock_client: VergeClient) -> None:
        """Test Certificate property accessors."""
        now_ts = int(time.time())
        data = {
            "$key": 1,
            "domain": "example.com",
            "domainname": "example.com",
            "domainlist": "www.example.com,api.example.com",
            "description": "Test certificate",
            "type": "self_signed",
            "key_type": "ecdsa",
            "rsa_key_size": "",
            "acme_server": "",
            "contact": 5,
            "agree_tos": True,
            "valid": True,
            "autocreated": False,
            "expires": now_ts + 86400 * 30,  # 30 days from now
            "created": now_ts - 86400,
            "modified": now_ts,
        }
        cert = Certificate(data, mock_client.certificates)

        assert cert.key == 1
        assert cert.domain == "example.com"
        assert cert.domain_name == "example.com"
        assert cert.domain_list == ["www.example.com", "api.example.com"]
        assert cert.description == "Test certificate"
        assert cert.cert_type == "self_signed"
        assert cert.cert_type_display == "Self-Signed"
        assert cert.key_type == "ecdsa"
        assert cert.key_type_display == "ECDSA"
        assert cert.rsa_key_size is None
        assert cert.acme_server == ""
        assert cert.contact_user_key == 5
        assert cert.is_tos_agreed is True
        assert cert.is_valid is True
        assert cert.is_auto_created is False
        assert cert.expires_at is not None
        assert cert.created_at is not None
        assert cert.modified_at is not None
        assert cert.days_until_expiry is not None
        assert 29 <= cert.days_until_expiry <= 30

    def test_certificate_default_values(self, mock_client: VergeClient) -> None:
        """Test Certificate default values for missing fields."""
        data = {"$key": 1}
        cert = Certificate(data, mock_client.certificates)

        assert cert.domain == ""
        assert cert.domain_name == ""
        assert cert.domain_list == []
        assert cert.description == ""
        assert cert.cert_type == ""
        assert cert.key_type == ""
        assert cert.key_type_display == ""
        assert cert.rsa_key_size is None
        assert cert.acme_server == ""
        assert cert.contact_user_key is None
        assert cert.is_tos_agreed is False
        assert cert.is_valid is False
        assert cert.is_auto_created is False
        assert cert.expires_at is None
        assert cert.created_at is None
        assert cert.modified_at is None
        assert cert.days_until_expiry is None

    def test_certificate_domain_fallback(self, mock_client: VergeClient) -> None:
        """Test domain falls back to domainname when domain is empty."""
        data = {"$key": 1, "domainname": "fallback.example.com"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.domain == "fallback.example.com"

    def test_certificate_type_display_manual(self, mock_client: VergeClient) -> None:
        """Test cert_type_display for manual certificate."""
        data = {"$key": 1, "type": "manual"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.cert_type_display == "Manual"

    def test_certificate_type_display_letsencrypt(self, mock_client: VergeClient) -> None:
        """Test cert_type_display for Let's Encrypt certificate."""
        data = {"$key": 1, "type": "letsencrypt"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.cert_type_display == "Let's Encrypt"

    def test_certificate_type_display_selfsigned(self, mock_client: VergeClient) -> None:
        """Test cert_type_display for self-signed certificate."""
        data = {"$key": 1, "type": "self_signed"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.cert_type_display == "Self-Signed"

    def test_certificate_key_type_rsa(self, mock_client: VergeClient) -> None:
        """Test key_type_display for RSA key."""
        data = {"$key": 1, "key_type": "rsa", "rsa_key_size": "4096"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.key_type_display == "RSA"
        assert cert.rsa_key_size == 4096

    def test_certificate_key_type_ecdsa(self, mock_client: VergeClient) -> None:
        """Test key_type_display for ECDSA key."""
        data = {"$key": 1, "key_type": "ecdsa"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.key_type_display == "ECDSA"

    def test_certificate_domain_list_empty(self, mock_client: VergeClient) -> None:
        """Test domain_list returns empty list when not set."""
        data = {"$key": 1, "domainlist": ""}
        cert = Certificate(data, mock_client.certificates)
        assert cert.domain_list == []

    def test_certificate_domain_list_single(self, mock_client: VergeClient) -> None:
        """Test domain_list with single domain."""
        data = {"$key": 1, "domainlist": "www.example.com"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.domain_list == ["www.example.com"]

    def test_certificate_domain_list_multiple(self, mock_client: VergeClient) -> None:
        """Test domain_list with multiple domains."""
        data = {"$key": 1, "domainlist": "www.example.com, api.example.com, admin.example.com"}
        cert = Certificate(data, mock_client.certificates)
        assert cert.domain_list == ["www.example.com", "api.example.com", "admin.example.com"]

    def test_certificate_expires_at_none(self, mock_client: VergeClient) -> None:
        """Test expires_at returns None when 0."""
        data = {"$key": 1, "expires": 0}
        cert = Certificate(data, mock_client.certificates)
        assert cert.expires_at is None

    def test_certificate_created_at_none(self, mock_client: VergeClient) -> None:
        """Test created_at returns None when 0."""
        data = {"$key": 1, "created": 0}
        cert = Certificate(data, mock_client.certificates)
        assert cert.created_at is None

    def test_certificate_modified_at_none(self, mock_client: VergeClient) -> None:
        """Test modified_at returns None when 0."""
        data = {"$key": 1, "modified": 0}
        cert = Certificate(data, mock_client.certificates)
        assert cert.modified_at is None

    def test_certificate_days_until_expiry_negative(self, mock_client: VergeClient) -> None:
        """Test days_until_expiry when certificate is expired."""
        past_ts = int(time.time()) - 86400 * 7  # 7 days ago
        data = {"$key": 1, "expires": past_ts}
        cert = Certificate(data, mock_client.certificates)
        assert cert.days_until_expiry is not None
        assert cert.days_until_expiry < 0

    def test_certificate_public_key(self, mock_client: VergeClient) -> None:
        """Test public_key property."""
        data = {"$key": 1, "public": "-----BEGIN CERTIFICATE-----\nMIID..."}
        cert = Certificate(data, mock_client.certificates)
        assert cert.public_key == "-----BEGIN CERTIFICATE-----\nMIID..."

    def test_certificate_private_key(self, mock_client: VergeClient) -> None:
        """Test private_key property."""
        data = {"$key": 1, "private": "-----BEGIN PRIVATE KEY-----\nMIIE..."}
        cert = Certificate(data, mock_client.certificates)
        assert cert.private_key == "-----BEGIN PRIVATE KEY-----\nMIIE..."

    def test_certificate_chain(self, mock_client: VergeClient) -> None:
        """Test chain property."""
        data = {"$key": 1, "chain": "-----BEGIN CERTIFICATE-----\nMIIC..."}
        cert = Certificate(data, mock_client.certificates)
        assert cert.chain == "-----BEGIN CERTIFICATE-----\nMIIC..."

    def test_certificate_keys_none(self, mock_client: VergeClient) -> None:
        """Test key properties return None when not loaded."""
        data = {"$key": 1}
        cert = Certificate(data, mock_client.certificates)
        assert cert.public_key is None
        assert cert.private_key is None
        assert cert.chain is None

    def test_certificate_repr(self, mock_client: VergeClient) -> None:
        """Test Certificate string representation."""
        data = {"$key": 1, "domain": "example.com", "type": "self_signed"}
        cert = Certificate(data, mock_client.certificates)

        repr_str = repr(cert)
        assert "Certificate" in repr_str
        assert "key=1" in repr_str
        assert "example.com" in repr_str
        assert "Self-Signed" in repr_str


# =============================================================================
# CertificateManager Tests
# =============================================================================


class TestCertificateManager:
    """Unit tests for CertificateManager."""

    def test_manager_endpoint(self, mock_client: VergeClient) -> None:
        """Test manager has correct endpoint."""
        assert mock_client.certificates._endpoint == "certificates"

    def test_list_certificates(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing certificates."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "example.com", "type": "self_signed"},
            {"$key": 2, "domain": "api.example.com", "type": "letsencrypt"},
        ]

        certs = mock_client.certificates.list()

        assert len(certs) == 2
        assert certs[0].domain == "example.com"
        assert certs[1].domain == "api.example.com"

    def test_list_certificates_empty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing certificates returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        certs = mock_client.certificates.list()
        assert certs == []

    def test_list_certificates_with_type_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing certificates with type filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "example.com", "type": "self_signed"}
        ]

        certs = mock_client.certificates.list(cert_type="SelfSigned")

        assert len(certs) == 1
        # Verify filter was applied
        call_args = mock_session.request.call_args
        assert "type eq 'self_signed'" in call_args.kwargs.get("params", {}).get(
            "filter", ""
        )

    def test_list_certificates_with_valid_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing certificates with valid filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "example.com", "valid": True}
        ]

        certs = mock_client.certificates.list(valid=True)

        assert len(certs) == 1
        call_args = mock_session.request.call_args
        assert "valid eq true" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_valid(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test list_valid convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "example.com", "valid": True}
        ]

        certs = mock_client.certificates.list_valid()

        assert len(certs) == 1
        call_args = mock_session.request.call_args
        assert "valid eq true" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_by_type(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test list_by_type convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "example.com", "type": "letsencrypt"}
        ]

        certs = mock_client.certificates.list_by_type("LetsEncrypt")

        assert len(certs) == 1
        call_args = mock_session.request.call_args
        assert "type eq 'letsencrypt'" in call_args.kwargs.get("params", {}).get(
            "filter", ""
        )

    def test_list_expiring(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test list_expiring convenience method."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "expiring.com", "expires": now_ts + 86400 * 15},  # 15 days
            {"$key": 2, "domain": "notexpiring.com", "expires": now_ts + 86400 * 90},  # 90 days
        ]

        certs = mock_client.certificates.list_expiring(days=30)

        assert len(certs) == 1
        assert certs[0].domain == "expiring.com"

    def test_list_expired(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test list_expired convenience method."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "expired.com", "expires": now_ts - 86400 * 7},  # 7 days ago
            {"$key": 2, "domain": "valid.com", "expires": now_ts + 86400 * 30},
        ]

        certs = mock_client.certificates.list_expired()

        assert len(certs) == 1
        assert certs[0].domain == "expired.com"

    def test_get_certificate_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting certificate by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "type": "self_signed",
        }

        cert = mock_client.certificates.get(1)

        assert cert.key == 1
        assert cert.domain == "example.com"

    def test_get_certificate_by_domain(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting certificate by domain."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "domain": "example.com", "type": "self_signed"}
        ]

        cert = mock_client.certificates.get(domain="example.com")

        assert cert.domain == "example.com"

    def test_get_certificate_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting non-existent certificate raises NotFoundError."""
        mock_session.request.return_value.status_code = 404
        mock_session.request.return_value.json.return_value = {"error": "Not found"}
        mock_session.request.return_value.text = "Not found"

        with pytest.raises(NotFoundError):
            mock_client.certificates.get(999)

    def test_get_certificate_no_params(self, mock_client: VergeClient) -> None:
        """Test getting certificate without key or domain raises ValueError."""
        with pytest.raises(ValueError, match="Either key or domain must be provided"):
            mock_client.certificates.get()

    def test_get_certificate_with_include_keys(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting certificate with include_keys=True."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "public": "-----BEGIN CERTIFICATE-----",
            "private": "-----BEGIN PRIVATE KEY-----",
            "chain": "-----BEGIN CERTIFICATE-----",
        }

        cert = mock_client.certificates.get(1, include_keys=True)

        assert cert.public_key is not None
        # Verify fields were requested
        call_args = mock_session.request.call_args
        fields = call_args.kwargs.get("params", {}).get("fields", "")
        assert "public" in fields
        assert "private" in fields
        assert "chain" in fields

    def test_create_certificate_selfsigned(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a self-signed certificate."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},  # POST response
            {  # GET response
                "$key": 1,
                "domain": "test.local",
                "type": "self_signed",
                "description": "Test cert",
            },
        ]

        cert = mock_client.certificates.create(
            domain="test.local",
            cert_type="SelfSigned",
            description="Test cert",
        )

        assert cert.domain == "test.local"
        assert cert.cert_type == "self_signed"

    def test_create_certificate_with_domain_list(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating certificate with domain list."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "test.local", "domainlist": "www.test.local,api.test.local"},
        ]

        mock_client.certificates.create(
            domain="test.local",
            domain_list=["www.test.local", "api.test.local"],
        )

        # Verify domain list was sent in request
        # Index 1 is the POST call (index 0 is system validation)
        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("domainlist") == "www.test.local,api.test.local"

    def test_create_certificate_with_domain_list_string(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating certificate with domain list as string."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "test.local"},
        ]

        mock_client.certificates.create(
            domain="test.local",
            domain_list="www.test.local,api.test.local",
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("domainlist") == "www.test.local,api.test.local"

    def test_create_certificate_manual(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a manual certificate."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "test.local", "type": "manual"},
        ]

        public_key = "-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----"
        private_key = "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----"

        mock_client.certificates.create(
            domain="test.local",
            cert_type="Manual",
            public_key=public_key,
            private_key=private_key,
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("public") == public_key
        assert body.get("private") == private_key
        assert body.get("type") == "manual"

    def test_create_certificate_manual_with_chain(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating manual certificate with chain."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "test.local", "type": "manual"},
        ]

        chain = "-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----"

        mock_client.certificates.create(
            domain="test.local",
            cert_type="Manual",
            public_key="-----BEGIN CERTIFICATE-----",
            private_key="-----BEGIN PRIVATE KEY-----",
            chain=chain,
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("chain") == chain

    def test_create_certificate_manual_missing_public_key(
        self, mock_client: VergeClient
    ) -> None:
        """Test creating manual certificate without public key raises error."""
        with pytest.raises(ValueError, match="public_key is required"):
            mock_client.certificates.create(
                domain="test.local",
                cert_type="Manual",
                private_key="-----BEGIN PRIVATE KEY-----",
            )

    def test_create_certificate_manual_missing_private_key(
        self, mock_client: VergeClient
    ) -> None:
        """Test creating manual certificate without private key raises error."""
        with pytest.raises(ValueError, match="private_key is required"):
            mock_client.certificates.create(
                domain="test.local",
                cert_type="Manual",
                public_key="-----BEGIN CERTIFICATE-----",
            )

    def test_create_certificate_letsencrypt(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a Let's Encrypt certificate."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "public.example.com", "type": "letsencrypt"},
        ]

        mock_client.certificates.create(
            domain="public.example.com",
            cert_type="LetsEncrypt",
            agree_tos=True,
            contact_user_key=1,
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("type") == "letsencrypt"
        assert body.get("agree_tos") is True
        assert body.get("contact") == 1

    def test_create_certificate_letsencrypt_missing_tos(
        self, mock_client: VergeClient
    ) -> None:
        """Test creating Let's Encrypt certificate without TOS agreement raises error."""
        with pytest.raises(ValueError, match="agree_tos must be True"):
            mock_client.certificates.create(
                domain="public.example.com",
                cert_type="LetsEncrypt",
            )

    def test_create_certificate_letsencrypt_with_acme_server(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating Let's Encrypt certificate with custom ACME server."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "test.example.com", "type": "letsencrypt"},
        ]

        mock_client.certificates.create(
            domain="test.example.com",
            cert_type="LetsEncrypt",
            agree_tos=True,
            acme_server="https://acme-staging-v02.api.letsencrypt.org/directory",
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("acme_server") == "https://acme-staging-v02.api.letsencrypt.org/directory"

    def test_create_certificate_letsencrypt_with_eab(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating Let's Encrypt certificate with EAB credentials."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "test.example.com", "type": "letsencrypt"},
        ]

        mock_client.certificates.create(
            domain="test.example.com",
            cert_type="LetsEncrypt",
            agree_tos=True,
            eab_key_id="kid_12345",
            eab_hmac_key="hmac_secret",
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("eab_kid") == "kid_12345"
        assert body.get("eab_hmac_key") == "hmac_secret"

    def test_create_certificate_with_key_type(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating certificate with specific key type."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "domain": "test.local", "key_type": "rsa"},
        ]

        mock_client.certificates.create(
            domain="test.local",
            key_type="RSA",
            rsa_key_size=4096,
        )

        post_call = mock_session.request.call_args_list[1]
        body = post_call.kwargs.get("json", {})
        assert body.get("key_type") == "rsa"
        assert body.get("rsa_key_size") == "4096"

    def test_update_certificate(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating a certificate."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "description": "Updated description",
        }

        cert = mock_client.certificates.update(1, description="Updated description")

        assert cert.description == "Updated description"

    def test_update_certificate_domain_list(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating certificate domain list."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "domainlist": "www.example.com,api.example.com",
        }

        mock_client.certificates.update(
            1, domain_list=["www.example.com", "api.example.com"]
        )

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("domainlist") == "www.example.com,api.example.com"

    def test_update_certificate_no_changes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating certificate with no changes returns current state."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
        }

        cert = mock_client.certificates.update(1)

        assert cert.key == 1

    def test_update_certificate_keys(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating certificate keys (manual cert)."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "type": "manual",
        }

        public_key = "-----BEGIN CERTIFICATE-----\nNEW...\n-----END CERTIFICATE-----"
        private_key = "-----BEGIN PRIVATE KEY-----\nNEW...\n-----END PRIVATE KEY-----"

        mock_client.certificates.update(
            1, public_key=public_key, private_key=private_key
        )

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("public") == public_key
        assert body.get("private") == private_key

    def test_delete_certificate(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test deleting a certificate."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.certificates.delete(1)

        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "certificates/1" in call_args.kwargs.get("url", "")

    def test_renew_certificate(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test renewing a certificate."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.side_effect = [
            # First call - get current cert
            {
                "$key": 1,
                "domain": "example.com",
                "type": "self_signed",
                "expires": now_ts + 86400 * 10,  # 10 days
            },
            # Second call - PUT to renew
            {},
            # Third call - get updated cert
            {
                "$key": 1,
                "domain": "example.com",
                "type": "self_signed",
                "expires": now_ts + 86400 * 365,  # 365 days
            },
        ]

        mock_client.certificates.renew(1, force=True)

        # Verify renew=True was sent
        put_call = mock_session.request.call_args_list[2]
        body = put_call.kwargs.get("json", {})
        assert body.get("renew") is True

    def test_renew_certificate_not_forced_not_expiring(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test renewing certificate without force when not near expiration."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "type": "self_signed",
            "expires": now_ts + 86400 * 90,  # 90 days - not expiring
        }

        cert = mock_client.certificates.renew(1, force=False)

        # Should only make one GET call and return existing cert
        assert cert.key == 1
        assert mock_session.request.call_count == 2  # system validation + GET

    def test_renew_certificate_manual_raises_error(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test renewing manual certificate raises error."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "type": "manual",
        }

        with pytest.raises(ValueError, match="Manual certificates cannot be renewed"):
            mock_client.certificates.renew(1, force=True)

    def test_refresh_certificate(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test refresh is alias for renew with force=True."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "domain": "example.com", "type": "self_signed", "expires": now_ts + 86400 * 90},
            {},
            {"$key": 1, "domain": "example.com", "type": "self_signed"},
        ]

        cert = mock_client.certificates.refresh(1)

        assert cert.key == 1


# =============================================================================
# Certificate Object Method Tests
# =============================================================================


class TestCertificateObjectMethods:
    """Unit tests for Certificate object methods."""

    def test_certificate_refresh(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test refreshing certificate via object method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "description": "Refreshed",
        }

        data = {"$key": 1, "domain": "example.com"}
        cert = Certificate(data, mock_client.certificates)

        refreshed = cert.refresh()

        assert refreshed.description == "Refreshed"

    def test_certificate_save(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test saving certificate via object method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "domain": "example.com",
            "description": "Saved",
        }

        data = {"$key": 1, "domain": "example.com"}
        cert = Certificate(data, mock_client.certificates)

        saved = cert.save(description="Saved")

        assert saved.description == "Saved"

    def test_certificate_delete(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test deleting certificate via object method."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        data = {"$key": 1, "domain": "example.com"}
        cert = Certificate(data, mock_client.certificates)

        cert.delete()

        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"

    def test_certificate_renew(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test renewing certificate via object method."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "domain": "example.com", "type": "self_signed", "expires": now_ts + 86400 * 90},
            {},
            {"$key": 1, "domain": "example.com", "type": "self_signed"},
        ]

        data = {"$key": 1, "domain": "example.com", "type": "self_signed", "expires": now_ts + 86400 * 90}
        cert = Certificate(data, mock_client.certificates)

        renewed = cert.renew(force=True)

        assert renewed.key == 1


# =============================================================================
# Mapping Tests
# =============================================================================


class TestMappings:
    """Unit tests for mapping constants."""

    def test_cert_type_map(self) -> None:
        """Test CERT_TYPE_MAP contains all certificate types."""
        assert "Manual" in CERT_TYPE_MAP
        assert "LetsEncrypt" in CERT_TYPE_MAP
        assert "SelfSigned" in CERT_TYPE_MAP

    def test_cert_type_display(self) -> None:
        """Test CERT_TYPE_DISPLAY contains all certificate types."""
        assert "manual" in CERT_TYPE_DISPLAY
        assert "letsencrypt" in CERT_TYPE_DISPLAY
        assert "self_signed" in CERT_TYPE_DISPLAY

    def test_key_type_map(self) -> None:
        """Test KEY_TYPE_MAP contains all key types."""
        assert "ECDSA" in KEY_TYPE_MAP
        assert "RSA" in KEY_TYPE_MAP

    def test_key_type_display(self) -> None:
        """Test KEY_TYPE_DISPLAY contains all key types."""
        assert "ecdsa" in KEY_TYPE_DISPLAY
        assert "rsa" in KEY_TYPE_DISPLAY
