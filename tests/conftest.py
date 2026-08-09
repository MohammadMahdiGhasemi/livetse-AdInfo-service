import os

os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/Promotion",
    "ADMIN_PASSWORD": "test-admin-secret-1234567890",
    "JWT_SECRET": "test-jwt-secret-that-is-long-enough-for-tests",
    "JWT_REQUIRE_EXP": "true",
    "UPLOAD_SERVICE_URL": "http://localhost:8000",
    "UPLOAD_SERVICE_API_KEY": "test-upload-key-1234567890",
    "LOG_JSON": "false",
    "ENABLE_DOCS": "true",
    "AUTO_CREATE_SCHEMA": "false",
})
