from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from zoneinfo import ZoneInfo

from redis import Redis

from packages.config.settings import settings

@dataclass
class LimitResult:
    ok: bool
    reason: str | None = None
    retry_at: str | None = None

def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)

def _incr_with_expiry(r: Redis, key: str, ttl_seconds: int) -> int:
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, ttl_seconds, nx=True)
    count, _ = pipe.execute()
    return int(count)

def _get_tz(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or settings.default_timezone)
    except Exception:
        return ZoneInfo(settings.default_timezone)

def quiet_hours_violation(user_tz: str | None, category: str) -> LimitResult:
    if category in {"otp", "transactional"}:
        return LimitResult(ok=True)
    now_local = datetime.now(_get_tz(user_tz))
    hour = now_local.hour
    start = settings.quiet_hours_start
    end = settings.quiet_hours_end
    in_quiet = hour >= start or hour < end if start > end else start <= hour < end
    if in_quiet:
        next_allowed = now_local.replace(hour=end, minute=0, second=0, microsecond=0)
        if hour >= start and start > end:
            next_allowed = next_allowed + timedelta(days=1)
        return LimitResult(ok=False, reason="quiet_hours", retry_at=next_allowed.isoformat())
    return LimitResult(ok=True)

def check_global_caps(category: str) -> LimitResult:
    r = get_redis()
    now = datetime.now(timezone.utc)
    hour_key = f"global:{category}:hour:{now.strftime('%Y%m%d%H')}"
    day_key = f"global:{category}:day:{now.strftime('%Y%m%d')}"
    hour_count = _incr_with_expiry(r, hour_key, 3700)
    day_count = _incr_with_expiry(r, day_key, 90000)
    if hour_count > settings.global_hourly_cap:
        return LimitResult(ok=False, reason="global_hourly_cap")
    if day_count > settings.global_daily_cap:
        return LimitResult(ok=False, reason="global_daily_cap")
    return LimitResult(ok=True)

def check_user_frequency(phone_e164: str, category: str) -> LimitResult:
    r = get_redis()
    now = datetime.now(timezone.utc)

    if category == "otp":
        cooldown_key = f"user:{phone_e164}:otp:cooldown"
        if r.exists(cooldown_key):
            ttl = r.ttl(cooldown_key)
            retry_at = (now + timedelta(seconds=max(ttl, 1))).isoformat()
            return LimitResult(ok=False, reason="otp_cooldown", retry_at=retry_at)
        r.setex(cooldown_key, settings.otp_cooldown_seconds, "1")
        hourly_key = f"user:{phone_e164}:otp:hour:{now.strftime('%Y%m%d%H')}"
        count = _incr_with_expiry(r, hourly_key, 3700)
        if count > settings.otp_max_per_hour:
            return LimitResult(ok=False, reason="otp_max_per_hour")
        return LimitResult(ok=True)

    if category == "promotional":
        day_key = f"user:{phone_e164}:promo:day:{now.strftime('%Y%m%d')}"
        week_key = f"user:{phone_e164}:promo:week:{now.strftime('%G%V')}"
        day_count = _incr_with_expiry(r, day_key, 90000)
        week_count = _incr_with_expiry(r, week_key, 700000)
        if day_count > settings.promo_max_per_day:
            return LimitResult(ok=False, reason="promo_max_per_day")
        if week_count > settings.promo_max_per_week:
            return LimitResult(ok=False, reason="promo_max_per_week")
        return LimitResult(ok=True)

    day_key = f"user:{phone_e164}:txn:day:{now.strftime('%Y%m%d')}"
    week_key = f"user:{phone_e164}:txn:week:{now.strftime('%G%V')}"
    day_count = _incr_with_expiry(r, day_key, 90000)
    week_count = _incr_with_expiry(r, week_key, 700000)
    if day_count > settings.txn_max_per_day:
        return LimitResult(ok=False, reason="txn_max_per_day")
    if week_count > settings.txn_max_per_week:
        return LimitResult(ok=False, reason="txn_max_per_week")
    return LimitResult(ok=True)

def check_duplicate_window(phone_e164: str, body: str) -> LimitResult:
    r = get_redis()
    normalized = " ".join(body.strip().lower().split())
    body_hash = hashlib.sha256(normalized.encode()).hexdigest()
    key = f"user:{phone_e164}:dup:{body_hash}"
    if r.exists(key):
        ttl = r.ttl(key)
        retry_at = (datetime.now(timezone.utc) + timedelta(seconds=max(ttl, 1))).isoformat()
        return LimitResult(ok=False, reason="duplicate_window", retry_at=retry_at)
    r.setex(key, settings.duplicate_window_minutes * 60, "1")
    return LimitResult(ok=True)
