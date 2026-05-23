"""
``python manage.py generate_vapid_keys``

Generates a fresh VAPID keypair and prints the env-file lines expected by
``config/settings.py``. Run once when setting up the project, paste the
output into the project ``.env``, restart Django + Celery.

Format note: ``pywebpush`` resolves ``vapid_private_key`` through
``py_vapid.Vapid.from_string``, which in the current py_vapid release
goes straight to ``from_der`` and base64url-decodes its input. So we emit
the private key as a single-line **base64url-encoded PKCS8 DER blob**
(no PEM headers, no escaped newlines) — that way the value drops into a
``.env`` file with no quoting tricks. The public key stays as the URL-safe
base64 of the uncompressed P-256 point because that's what the browser's
``PushManager.subscribe({applicationServerKey})`` needs.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


class Command(BaseCommand):
    help = 'Generate a VAPID keypair and print env-file lines to paste into .env'

    def handle(self, *args, **options) -> None:
        vapid = Vapid()
        vapid.generate_keys()

        # Private key as base64url-encoded PKCS8 DER. This is the format
        # pywebpush's current Vapid.from_string expects: it b64url-decodes
        # the value and feeds the bytes to load_der_private_key.
        der_bytes = vapid.private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        private_b64 = _b64url(der_bytes)

        # Public key — raw uncompressed P-256 point in URL-safe base64.
        # That's the on-wire form the browser's PushManager expects via
        # ``applicationServerKey``.
        public_bytes = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        public_b64 = _b64url(public_bytes)

        self.stdout.write(self.style.SUCCESS(
            'Add these three lines to your .env (overwrite any existing VAPID_*):\n',
        ))
        self.stdout.write(f"VAPID_PUBLIC_KEY={public_b64}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private_b64}")
        self.stdout.write("VAPID_CLAIM_SUB=mailto:your-admin@example.com")
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            'Restart the app/celery containers so the new keys are picked up,\n'
            'then ask each subscribed user to re-enable push notifications —\n'
            'their existing browser subscriptions were bound to the old key.',
        ))
