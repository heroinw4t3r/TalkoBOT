import base64
import datetime as dt
import hashlib
import hmac

def hour_floor_utc(now: dt.datetime | None = None) -> dt.datetime:
    now = now or dt.datetime.utcnow()
    return now.replace(minute=0, second=0, microsecond=0, tzinfo=None)

def derive_password(secret: str, at: dt.datetime | None = None, length: int = 8) -> str:
    at = hour_floor_utc(at)
    msg = at.strftime("%Y%m%d%H").encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")[:length]

def current_version_key(at: dt.datetime | None = None) -> str:
    at = hour_floor_utc(at)
    return at.strftime("%Y%m%d%H")