import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Generate an ephemeral RSA keypair before application settings are imported.
# Tests sign with the private key; the service only receives the public key.
_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEST_PRIVATE_KEY = _test_private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
TEST_PUBLIC_KEY = _test_private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/Promotion",
    "JWT_PUBLIC_KEY": TEST_PUBLIC_KEY,
    "JWT_REQUIRE_EXP": "true",
    "ADMIN_ROLES": "ADMIN,SUPER_ADMIN",
    "UPLOAD_SERVICE_URL": "http://localhost:8000",
    "UPLOAD_SERVICE_API_KEY": "test-upload-key-1234567890",
    "LOG_JSON": "false",
    "ENABLE_DOCS": "true",
    "AUTO_CREATE_SCHEMA": "false",
})
