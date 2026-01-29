"""Integration tests for Certificate operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import uuid

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.certificates import Certificate


def unique_domain(prefix: str = "pyvergeos-test") -> str:
    """Generate a unique domain name for test resources."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}.local"


@pytest.fixture
def test_cert_domain() -> str:
    """Generate a unique test certificate domain."""
    return unique_domain("pyvergeos-cert")


@pytest.fixture
def test_certificate(live_client: VergeClient, test_cert_domain: str):
    """Create and cleanup a test certificate."""
    cert = live_client.certificates.create(
        domain=test_cert_domain,
        cert_type="SelfSigned",
        description="Integration test certificate",
    )

    yield cert

    # Cleanup
    try:  # noqa: SIM105
        live_client.certificates.delete(cert.key)
    except NotFoundError:
        pass  # Already deleted


@pytest.mark.integration
class TestCertificateListIntegration:
    """Integration tests for CertificateManager list operations."""

    def test_list_certificates(self, live_client: VergeClient) -> None:
        """Test listing certificates from live system."""
        certs = live_client.certificates.list()

        # Should return a list (may be empty but usually has at least system cert)
        assert isinstance(certs, list)

        # Each certificate should have expected properties
        for cert in certs:
            assert hasattr(cert, "key")
            assert hasattr(cert, "domain")
            assert hasattr(cert, "cert_type")
            assert hasattr(cert, "is_valid")

    def test_list_certificates_with_limit(self, live_client: VergeClient) -> None:
        """Test listing certificates with limit."""
        certs = live_client.certificates.list(limit=1)

        assert isinstance(certs, list)
        assert len(certs) <= 1

    def test_list_certificates_with_type_filter(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test listing certificates with type filter."""
        certs = live_client.certificates.list(cert_type="SelfSigned")

        assert isinstance(certs, list)
        for cert in certs:
            assert cert.cert_type == "self_signed"

    def test_list_valid_certificates(self, live_client: VergeClient) -> None:
        """Test listing only valid certificates."""
        certs = live_client.certificates.list_valid()

        assert isinstance(certs, list)
        for cert in certs:
            assert cert.is_valid is True

    def test_list_by_type(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test list_by_type convenience method."""
        certs = live_client.certificates.list_by_type("SelfSigned")

        assert isinstance(certs, list)
        assert len(certs) >= 1
        for cert in certs:
            assert cert.cert_type == "self_signed"

    def test_list_expiring(self, live_client: VergeClient) -> None:
        """Test listing expiring certificates."""
        # List certs expiring in 400 days to catch most/all certs
        certs = live_client.certificates.list_expiring(days=400)

        assert isinstance(certs, list)
        for cert in certs:
            assert cert.days_until_expiry is not None
            assert cert.days_until_expiry < 400

    def test_list_expired(self, live_client: VergeClient) -> None:
        """Test listing expired certificates."""
        certs = live_client.certificates.list_expired()

        assert isinstance(certs, list)
        # All returned certs should be expired
        for cert in certs:
            assert cert.days_until_expiry is not None
            assert cert.days_until_expiry < 0


@pytest.mark.integration
class TestCertificateGetIntegration:
    """Integration tests for CertificateManager get operations."""

    def test_get_certificate_by_key(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test getting a certificate by key."""
        fetched = live_client.certificates.get(test_certificate.key)

        assert fetched.key == test_certificate.key
        assert fetched.domain == test_certificate.domain

    def test_get_certificate_by_domain(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test getting a certificate by domain."""
        fetched = live_client.certificates.get(domain=test_certificate.domain)

        assert fetched.key == test_certificate.key
        assert fetched.domain == test_certificate.domain

    def test_get_certificate_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent certificate."""
        with pytest.raises(NotFoundError):
            live_client.certificates.get(domain="non-existent-cert-12345.local")

    def test_get_certificate_with_include_keys(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test getting certificate with key material."""
        fetched = live_client.certificates.get(
            test_certificate.key, include_keys=True
        )

        assert fetched.key == test_certificate.key
        # Public key should be present for self-signed
        assert fetched.public_key is not None


@pytest.mark.integration
class TestCertificateCRUDIntegration:
    """Integration tests for Certificate CRUD operations."""

    def test_create_and_delete_certificate(
        self, live_client: VergeClient, test_cert_domain: str
    ) -> None:
        """Test creating and deleting a self-signed certificate."""
        cert = live_client.certificates.create(
            domain=test_cert_domain,
            cert_type="SelfSigned",
            description="CRUD test certificate",
            key_type="ECDSA",
        )

        try:
            assert cert.domain == test_cert_domain
            assert cert.cert_type == "self_signed"
            assert cert.description == "CRUD test certificate"
            assert cert.key_type == "ecdsa"

            # Verify it exists
            fetched = live_client.certificates.get(cert.key)
            assert fetched.key == cert.key
        finally:
            # Cleanup
            live_client.certificates.delete(cert.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.certificates.get(domain=test_cert_domain)

    def test_create_certificate_with_domain_list(
        self, live_client: VergeClient, test_cert_domain: str
    ) -> None:
        """Test creating certificate with SANs."""
        san1 = f"www.{test_cert_domain}"
        san2 = f"api.{test_cert_domain}"

        cert = live_client.certificates.create(
            domain=test_cert_domain,
            cert_type="SelfSigned",
            domain_list=[san1, san2],
        )

        try:
            assert cert.domain == test_cert_domain
            assert san1 in cert.domain_list or "www." in str(cert.domain_list)
        finally:
            live_client.certificates.delete(cert.key)

    def test_create_certificate_rsa_key(
        self, live_client: VergeClient, test_cert_domain: str
    ) -> None:
        """Test creating certificate with RSA key type."""
        cert = live_client.certificates.create(
            domain=test_cert_domain,
            cert_type="SelfSigned",
            key_type="RSA",
            rsa_key_size=2048,
        )

        try:
            assert cert.key_type == "rsa"
            assert cert.rsa_key_size == 2048
        finally:
            live_client.certificates.delete(cert.key)

    def test_update_certificate(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test updating a certificate."""
        new_description = "Updated description"
        updated = live_client.certificates.update(
            test_certificate.key,
            description=new_description,
        )

        assert updated.description == new_description

    def test_update_certificate_domain_list(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test updating certificate domain list."""
        new_san = f"new.{test_certificate.domain}"
        updated = live_client.certificates.update(
            test_certificate.key,
            domain_list=[new_san],
        )

        assert new_san in updated.domain_list or "new." in str(updated.domain_list)


@pytest.mark.integration
class TestCertificateRenewIntegration:
    """Integration tests for certificate renewal operations."""

    def test_renew_certificate_forced(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test forcing certificate renewal/regeneration."""
        original_key = test_certificate.key

        renewed = live_client.certificates.renew(original_key, force=True)

        assert renewed.key == original_key
        assert renewed.domain == test_certificate.domain

    def test_renew_via_object_method(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test renewing via certificate object method."""
        renewed = test_certificate.renew(force=True)

        assert renewed.key == test_certificate.key

    def test_refresh_certificate(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test refresh method (alias for forced renew)."""
        refreshed = live_client.certificates.refresh(test_certificate.key)

        assert refreshed.key == test_certificate.key


@pytest.mark.integration
class TestCertificateObjectMethodsIntegration:
    """Integration tests for certificate object methods."""

    def test_certificate_refresh(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test refreshing certificate data via object method."""
        refreshed = test_certificate.refresh()

        assert refreshed.key == test_certificate.key
        assert refreshed.domain == test_certificate.domain

    def test_certificate_save(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test saving certificate via object method."""
        saved = test_certificate.save(description="Saved via object method")

        assert saved.description == "Saved via object method"

    def test_certificate_delete(
        self, live_client: VergeClient, test_cert_domain: str
    ) -> None:
        """Test deleting certificate via object method."""
        # Create a cert specifically for this test
        cert = live_client.certificates.create(
            domain=test_cert_domain,
            cert_type="SelfSigned",
        )

        # Delete via object method
        cert.delete()

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.certificates.get(domain=test_cert_domain)


@pytest.mark.integration
class TestCertificatePropertiesIntegration:
    """Integration tests for certificate property accessors."""

    def test_certificate_properties(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test certificate properties are populated correctly."""
        assert test_certificate.key is not None
        assert test_certificate.domain != ""
        assert test_certificate.cert_type in ("self_signed", "manual", "letsencrypt")
        assert test_certificate.cert_type_display in ("Self-Signed", "Manual", "Let's Encrypt")

        # Dates may or may not be populated depending on API response
        # Just verify the properties are accessible
        _ = test_certificate.created_at
        _ = test_certificate.expires_at
        _ = test_certificate.days_until_expiry

    def test_certificate_display_properties(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test certificate display property formatting."""
        assert test_certificate.cert_type_display == "Self-Signed"
        assert test_certificate.key_type_display in ("ECDSA", "RSA", "")

    def test_certificate_repr(
        self, live_client: VergeClient, test_certificate: Certificate
    ) -> None:
        """Test certificate string representation."""
        repr_str = repr(test_certificate)

        assert "Certificate" in repr_str
        assert str(test_certificate.key) in repr_str
        assert test_certificate.domain in repr_str


@pytest.mark.integration
class TestCertificateEdgeCasesIntegration:
    """Integration tests for certificate edge cases."""

    def test_certificate_with_long_domain(
        self, live_client: VergeClient
    ) -> None:
        """Test creating certificate with longer domain name."""
        long_domain = f"pyvergeos-test-{uuid.uuid4().hex}.local"

        cert = live_client.certificates.create(
            domain=long_domain,
            cert_type="SelfSigned",
        )

        try:
            assert cert.domain == long_domain
        finally:
            live_client.certificates.delete(cert.key)

    def test_certificate_with_subdomain(
        self, live_client: VergeClient, test_cert_domain: str
    ) -> None:
        """Test creating certificate with subdomain."""
        subdomain = f"sub.{test_cert_domain}"

        cert = live_client.certificates.create(
            domain=subdomain,
            cert_type="SelfSigned",
        )

        try:
            assert cert.domain == subdomain
        finally:
            live_client.certificates.delete(cert.key)

    def test_get_system_certificate(self, live_client: VergeClient) -> None:
        """Test getting the system certificate (usually key 1)."""
        # Most VergeOS systems have a system cert at key 1
        try:
            cert = live_client.certificates.get(1)
            assert cert.key == 1
            assert cert.domain != ""
        except NotFoundError:
            pytest.skip("System certificate not found at key 1")
