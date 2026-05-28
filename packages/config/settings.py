from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str
    redis_url: str

    message_provider: str = "local_mock"
    sms_provider: str = "local_mock"
    sms_api_key: str = ""
    sms_api_secret: str = ""
    sms_sender_id: str = ""
    sms_webhook_secret: str = ""

    email_provider: str = "mailpit"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@example.com"

    # Legacy compatibility only.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_messaging_service_sid: str = ""
    twilio_status_callback_url: str = ""
    twilio_inbound_webhook_url: str = ""
    twilio_validate_signature: bool = False

    public_base_url: str = "http://localhost:8001"
    default_timezone: str = "America/New_York"
    quiet_hours_start: int = 21
    quiet_hours_end: int = 8
    promo_max_per_day: int = 1
    promo_max_per_week: int = 3
    txn_max_per_day: int = 5
    txn_max_per_week: int = 20
    otp_cooldown_seconds: int = 45
    otp_max_per_hour: int = 3
    global_hourly_cap: int = 10000
    global_daily_cap: int = 100000
    duplicate_window_minutes: int = 60

    # DEPRECATED: Use JWT authentication instead
    admin_api_keys: str = ""
    
    campaign_batch_size: int = 100
    campaign_batch_interval_seconds: int = 60
    retry_max_attempts: int = 3
    retry_backoff_seconds: int = 120
    
    # JWT Configuration
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 15
    jwt_refresh_expiration_days: int = 7
    
    # Security Settings
    allowed_origins: list = ["http://localhost:3000", "http://localhost:8001"]
    require_https: bool = False  # Set to True in production
    max_login_attempts: int = 5
    login_lockout_minutes: int = 15
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special_chars: bool = True

settings = Settings()
