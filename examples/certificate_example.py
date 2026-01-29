#!/usr/bin/env python3
"""Examples for VergeOS SSL/TLS certificate management.

This script demonstrates certificate management capabilities:
- Listing and filtering certificates
- Creating self-signed certificates
- Creating manual certificates (uploading existing certs)
- Modifying certificate properties
- Renewing and regenerating certificates
- Certificate expiration monitoring
- Common certificate workflows

Prerequisites:
- Python 3.9 or later
- pyvergeos package installed
- Environment variables configured (VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD)
  OR modify the connection section below

Certificate Types:
- Manual: Upload your own certificate and private key
- LetsEncrypt: Automatically obtain via ACME protocol (requires public DNS)
- SelfSigned: Generate a self-signed certificate
"""

from __future__ import annotations

import os
import sys

# Add parent directory to path for development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyvergeos import VergeClient

# =============================================================================
# CONNECTION
# =============================================================================


def get_client() -> VergeClient:
    """Get a connected VergeClient.

    Uses environment variables by default. Modify this function
    to use hardcoded credentials for testing (not recommended for production).
    """
    # Option 1: Use environment variables (recommended)
    # Set these in your shell:
    #   export VERGE_HOST=your-vergeos-host
    #   export VERGE_USERNAME=admin
    #   export VERGE_PASSWORD=your-password
    #   export VERGE_VERIFY_SSL=false

    if os.environ.get("VERGE_HOST"):
        return VergeClient.from_env()

    # Option 2: Direct connection (for development only)
    # Uncomment and modify these lines:
    # return VergeClient(
    #     host="192.168.1.100",
    #     username="admin",
    #     password="your-password",
    #     verify_ssl=False,
    # )

    raise RuntimeError(
        "No VergeOS credentials configured. "
        "Set VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD environment variables."
    )


# =============================================================================
# LISTING CERTIFICATES
# =============================================================================


def example_list_certificates(client: VergeClient) -> None:
    """Demonstrate listing and filtering certificates."""
    print("\n" + "=" * 60)
    print("LISTING AND FILTERING CERTIFICATES")
    print("=" * 60)

    # List all certificates
    print("\n--- All certificates ---")
    certs = client.certificates.list()
    print(f"Found {len(certs)} certificates")

    for cert in certs:
        print(f"  [{cert.key}] {cert.domain}")
        print(f"       Type: {cert.cert_type_display}")
        print(f"       Valid: {cert.is_valid}")
        if cert.expires_at:
            print(f"       Expires: {cert.expires_at}")
            if cert.days_until_expiry is not None:
                print(f"       Days until expiry: {cert.days_until_expiry}")

    # Filter by certificate type
    print("\n--- Self-signed certificates ---")
    self_signed = client.certificates.list_by_type("SelfSigned")
    print(f"Found {len(self_signed)} self-signed certificates")
    for cert in self_signed:
        print(f"  [{cert.key}] {cert.domain}")

    # Get only valid (unexpired) certificates
    print("\n--- Valid certificates ---")
    valid = client.certificates.list_valid()
    print(f"Found {len(valid)} valid certificates")

    # Get a specific certificate by key
    if certs:
        print(f"\n--- Get certificate by key ({certs[0].key}) ---")
        cert = client.certificates.get(certs[0].key)
        print(f"Domain: {cert.domain}")
        print(f"Type: {cert.cert_type_display}")
        print(f"Key type: {cert.key_type_display}")


# =============================================================================
# CREATING CERTIFICATES
# =============================================================================


def example_create_self_signed(client: VergeClient) -> None:
    """Demonstrate creating self-signed certificates."""
    print("\n" + "=" * 60)
    print("CREATING SELF-SIGNED CERTIFICATES")
    print("=" * 60)

    # Create a basic self-signed certificate
    print("\n--- Create basic self-signed certificate ---")
    cert = client.certificates.create(
        domain="myapp.local",
        cert_type="SelfSigned",
        description="Example self-signed certificate",
    )
    print(f"Created: {cert.domain} (key: {cert.key})")
    print(f"  Type: {cert.cert_type_display}")
    print(f"  Key type: {cert.key_type_display}")

    # Cleanup
    client.certificates.delete(cert.key)
    print("  Deleted certificate")

    # Create with specific key type
    print("\n--- Create RSA certificate ---")
    cert = client.certificates.create(
        domain="secure.local",
        cert_type="SelfSigned",
        key_type="RSA",
        rsa_key_size=4096,
        description="RSA 4096-bit certificate",
    )
    print(f"Created: {cert.domain} (key: {cert.key})")
    print(f"  Key type: {cert.key_type_display}")
    print(f"  RSA key size: {cert.rsa_key_size}")

    # Cleanup
    client.certificates.delete(cert.key)
    print("  Deleted certificate")

    # Create with Subject Alternative Names (SANs)
    print("\n--- Create certificate with SANs ---")
    cert = client.certificates.create(
        domain="app.local",
        cert_type="SelfSigned",
        domain_list=["www.app.local", "api.app.local", "admin.app.local"],
        description="Multi-domain certificate",
    )
    print(f"Created: {cert.domain} (key: {cert.key})")
    print(f"  SANs: {cert.domain_list}")

    # Cleanup
    client.certificates.delete(cert.key)
    print("  Deleted certificate")


def example_create_manual(client: VergeClient) -> None:
    """Demonstrate creating manual (uploaded) certificates.

    Note: This example uses placeholder certificate content.
    Replace with real PEM-formatted certificates for actual use.
    """
    print("\n" + "=" * 60)
    print("CREATING MANUAL CERTIFICATES (Placeholder)")
    print("=" * 60)

    # Example with placeholder content (would fail without real certs)
    print("\n--- Manual certificate creation syntax ---")
    print("""
    # Read certificate files
    with open("cert.pem", "r") as f:
        public_key = f.read()
    with open("key.pem", "r") as f:
        private_key = f.read()
    with open("chain.pem", "r") as f:
        chain = f.read()

    # Upload the certificate
    cert = client.certificates.create(
        domain="example.com",
        cert_type="Manual",
        public_key=public_key,
        private_key=private_key,
        chain=chain,
        description="Uploaded production certificate",
    )
    """)


def example_create_letsencrypt(client: VergeClient) -> None:
    """Demonstrate Let's Encrypt certificate creation syntax.

    Note: Let's Encrypt requires:
    - Public DNS pointing to the VergeOS system
    - Port 80 or DNS-01 challenge capability
    """
    print("\n" + "=" * 60)
    print("LET'S ENCRYPT CERTIFICATES (Syntax Only)")
    print("=" * 60)

    print("""
    # Create a Let's Encrypt certificate
    # Note: Requires proper DNS/HTTP validation setup
    cert = client.certificates.create(
        domain="public.example.com",
        cert_type="LetsEncrypt",
        agree_tos=True,
        contact_user_key=1,  # User key for ACME notifications
        description="Let's Encrypt production certificate",
    )

    # Create with staging server (for testing)
    cert = client.certificates.create(
        domain="test.example.com",
        cert_type="LetsEncrypt",
        acme_server="https://acme-staging-v02.api.letsencrypt.org/directory",
        agree_tos=True,
        contact_user_key=1,
    )

    # Create with External Account Binding (for providers that require it)
    cert = client.certificates.create(
        domain="eab.example.com",
        cert_type="LetsEncrypt",
        acme_server="https://acme.provider.com/directory",
        eab_key_id="kid_12345",
        eab_hmac_key="hmac_secret_key",
        agree_tos=True,
        contact_user_key=1,
    )
    """)


# =============================================================================
# MODIFYING CERTIFICATES
# =============================================================================


def example_modify_certificates(client: VergeClient) -> None:
    """Demonstrate modifying certificate properties."""
    print("\n" + "=" * 60)
    print("MODIFYING CERTIFICATE PROPERTIES")
    print("=" * 60)

    # Create a test certificate
    cert = client.certificates.create(
        domain="modify-test.local",
        cert_type="SelfSigned",
        description="Original description",
    )
    print(f"\nCreated test certificate: {cert.domain} (key: {cert.key})")

    # Update description using manager
    print("\n--- Update description via manager ---")
    cert = client.certificates.update(
        cert.key,
        description="Updated description via manager",
    )
    print(f"New description: {cert.description}")

    # Update using object method (save)
    print("\n--- Update via object method ---")
    cert = cert.save(description="Updated via object save method")
    print(f"New description: {cert.description}")

    # Update domain list (SANs)
    print("\n--- Update SANs ---")
    cert = client.certificates.update(
        cert.key,
        domain_list=["www.modify-test.local", "api.modify-test.local"],
    )
    print(f"New SANs: {cert.domain_list}")

    # Cleanup
    client.certificates.delete(cert.key)
    print("\nDeleted test certificate")


# =============================================================================
# RENEWING CERTIFICATES
# =============================================================================


def example_renew_certificates(client: VergeClient) -> None:
    """Demonstrate certificate renewal/regeneration."""
    print("\n" + "=" * 60)
    print("RENEWING AND REGENERATING CERTIFICATES")
    print("=" * 60)

    # Create a test certificate
    cert = client.certificates.create(
        domain="renew-test.local",
        cert_type="SelfSigned",
        description="Certificate for renewal test",
    )
    print(f"\nCreated test certificate: {cert.domain} (key: {cert.key})")

    # Regenerate a self-signed certificate (creates new key pair)
    print("\n--- Regenerate certificate via manager ---")
    cert = client.certificates.renew(cert.key, force=True)
    print(f"Regenerated: {cert.domain}")

    # Renew via object method
    print("\n--- Renew via object method ---")
    cert = cert.renew(force=True)
    print(f"Renewed: {cert.domain}")

    # Refresh (alias for forced renew)
    print("\n--- Refresh certificate ---")
    cert = client.certificates.refresh(cert.key)
    print(f"Refreshed: {cert.domain}")

    # Cleanup
    client.certificates.delete(cert.key)
    print("\nDeleted test certificate")


# =============================================================================
# CERTIFICATE EXPIRATION MONITORING
# =============================================================================


def example_expiration_monitoring(client: VergeClient) -> None:
    """Demonstrate certificate expiration monitoring."""
    print("\n" + "=" * 60)
    print("CERTIFICATE EXPIRATION MONITORING")
    print("=" * 60)

    # List certificates sorted by expiration
    print("\n--- Certificates by expiration ---")
    certs = client.certificates.list()
    certs_with_expiry = [c for c in certs if c.days_until_expiry is not None]
    certs_sorted = sorted(certs_with_expiry, key=lambda c: c.days_until_expiry or 0)

    for cert in certs_sorted:
        status = "EXPIRED" if (cert.days_until_expiry or 0) < 0 else "OK"
        print(f"  [{status:7}] {cert.domain}: {cert.days_until_expiry} days")

    # Find certificates expiring soon
    print("\n--- Certificates expiring within 90 days ---")
    expiring = client.certificates.list_expiring(days=90)
    if expiring:
        for cert in expiring:
            print(f"  {cert.domain}: {cert.days_until_expiry} days until expiry")
    else:
        print("  No certificates expiring within 90 days")

    # Find expired certificates
    print("\n--- Expired certificates ---")
    expired = client.certificates.list_expired()
    if expired:
        for cert in expired:
            print(f"  {cert.domain}: expired {abs(cert.days_until_expiry or 0)} days ago")
    else:
        print("  No expired certificates")

    # Certificate health summary
    print("\n--- Certificate Health Summary ---")
    total = len(certs)
    valid = len([c for c in certs if c.is_valid])
    expired_count = len(expired)
    critical = len([c for c in certs_with_expiry if 0 <= (c.days_until_expiry or 0) < 7])
    warning = len([c for c in certs_with_expiry if 7 <= (c.days_until_expiry or 0) < 30])

    print(f"  Total certificates: {total}")
    print(f"  Valid: {valid}")
    print(f"  Expired: {expired_count}")
    print(f"  Critical (< 7 days): {critical}")
    print(f"  Warning (< 30 days): {warning}")


# =============================================================================
# PRACTICAL WORKFLOWS
# =============================================================================


def example_auto_renewal_workflow(client: VergeClient) -> None:
    """Demonstrate auto-renewal workflow."""
    print("\n" + "=" * 60)
    print("AUTO-RENEWAL WORKFLOW")
    print("=" * 60)

    print("""
    # Auto-renew certificates expiring within threshold
    def auto_renew_certificates(client, days_threshold=14):
        expiring = client.certificates.list_expiring(days=days_threshold)

        for cert in expiring:
            # Skip manual certificates (can't auto-renew)
            if cert.cert_type == "manual":
                print(f"Skipping manual cert: {cert.domain}")
                continue

            try:
                print(f"Renewing: {cert.domain}")
                client.certificates.renew(cert.key, force=True)
                print(f"  Success!")
            except Exception as e:
                print(f"  Failed: {e}")

    # Run auto-renewal
    auto_renew_certificates(client, days_threshold=30)
    """)


def example_certificate_inventory(client: VergeClient) -> None:
    """Demonstrate certificate inventory export."""
    print("\n" + "=" * 60)
    print("CERTIFICATE INVENTORY")
    print("=" * 60)

    certs = client.certificates.list()

    print("\n--- Certificate Inventory ---")
    print(f"{'Key':<5} {'Domain':<30} {'Type':<12} {'Valid':<6} {'Expires':<12}")
    print("-" * 70)

    for cert in certs:
        expires = "N/A"
        if cert.days_until_expiry is not None:
            expires = f"{cert.days_until_expiry}d"

        print(
            f"{cert.key:<5} {cert.domain[:29]:<30} {cert.cert_type_display:<12} "
            f"{'Yes' if cert.is_valid else 'No':<6} {expires:<12}"
        )

    print(f"\nTotal: {len(certs)} certificates")


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    """Run certificate management examples."""
    print("VergeOS Certificate Management Examples")
    print("=" * 60)

    try:
        client = get_client()
        print(f"Connected to VergeOS {client.version}")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    try:
        # Run examples
        example_list_certificates(client)
        example_create_self_signed(client)
        example_create_manual(client)
        example_create_letsencrypt(client)
        example_modify_certificates(client)
        example_renew_certificates(client)
        example_expiration_monitoring(client)
        example_auto_renewal_workflow(client)
        example_certificate_inventory(client)

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during examples: {e}")
        raise
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
