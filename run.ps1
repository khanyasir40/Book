param(
  [string]$SecretKey = "dev-secret-key",
  [string]$AdminEmail = "admin@example.com",
  [string]$AdminPassword = "admin1234",
  [string]$TestUserEmail = "test@example.com",
  [string]$TestUserPassword = "test1234"
)

# Create and activate venv
if (!(Test-Path ".venv")) { py -m venv .venv }
. .\.venv\Scripts\Activate.ps1

# Install deps
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

# Set env vars
$env:SECRET_KEY = $SecretKey
$env:ADMIN_EMAIL = $AdminEmail
$env:ADMIN_PASSWORD = $AdminPassword
$env:TEST_USER_EMAIL = $TestUserEmail
$env:TEST_USER_PASSWORD = $TestUserPassword

# Start server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload