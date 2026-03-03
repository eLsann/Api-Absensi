from datetime import datetime, timezone
import os

from app.config import settings


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def save_snapshot_bytes(img_bytes: bytes, *, reason: str, device_id: str) -> str:
    ensure_dir(settings.snapshot_dir)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    fn = f"{ts}_{device_id}_{reason}.jpg"
    path = os.path.join(settings.snapshot_dir, fn)
    with open(path, "wb") as f:
        f.write(img_bytes)
    return path
