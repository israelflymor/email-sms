from pydantic_settings import BaseSettings, SettingsConfigDict

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

    admin_api_keys: str = "admin_key_123:admin,review_key_123:reviewer,ops_key_123:operator,view_key_123:viewer"
    campaign_batch_size: int = 100
    campaign_batch_interval_seconds: int = 60
    retry_max_attempts: int = 3
    retry_backoff_seconds: int = 120

settings = Settings()
