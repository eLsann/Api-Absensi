import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
    # --- app ---
    app_name: str = os.getenv("APP_NAME", "Project Absensi API")
    env: str = os.getenv("ENV", "production")
    timezone: str = os.getenv("TZ", "Asia/Jakarta") # Default to Jakarta for home server


    # Database — wajib di-set via env var, tidak ada default berbahaya
    database_url: str = os.getenv("DATABASE_URL", "").strip()

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return self.database_url

    # --- security/admin ---
    secret_key: str = os.getenv("SECRET_KEY", "").strip()
    admin_token_expire_hours: int = int(os.getenv("ADMIN_TOKEN_EXPIRE_HOURS", "8"))
    default_admin_user: str = os.getenv("DEFAULT_ADMIN_USER", "").strip()
    default_admin_password: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "").strip()

    @property
    def SECRET_KEY(self) -> str:  # noqa: N802
        return self.secret_key

    @property
    def ADMIN_TOKEN_EXPIRE_HOURS(self) -> int:  # noqa: N802
        return self.admin_token_expire_hours

    @property
    def DEFAULT_ADMIN_USER(self) -> str:  # noqa: N802
        return self.default_admin_user

    @property
    def DEFAULT_ADMIN_PASSWORD(self) -> str:  # noqa: N802
        return self.default_admin_password

    # --- device tokens ---
    device_tokens: str = os.getenv("DEVICE_TOKENS", "").strip()

    @property
    def DEVICE_TOKENS(self) -> str:  # noqa: N802
        return self.device_tokens

    # --- face recognition ---
    max_distance: float = float(os.getenv("MAX_DISTANCE", "0.85"))
    # min_face_px default=80 sesuai MTCNN min_face_size di recog.py
    # (sebelumnya 50, konflik dengan MTCNN yang tidak deteksi < 80px)
    min_face_px: int = int(os.getenv("MIN_FACE_PX", "80"))
    # Confidence threshold untuk MTCNN detection (0.0-1.0)
    detection_confidence: float = float(os.getenv("DETECTION_CONFIDENCE", "0.9"))

    @property
    def MAX_DISTANCE(self) -> float:  # noqa: N802
        return self.max_distance

    @property
    def MIN_FACE_PX(self) -> int:  # noqa: N802
        return self.min_face_px

    # --- attendance/cooldown ---
    cooldown_seconds: int = int(os.getenv("COOLDOWN_SECONDS", "45"))

    # --- database connection retry ---
    db_max_retries: int = int(os.getenv("DB_MAX_RETRIES", "30"))
    db_retry_interval: int = int(os.getenv("DB_RETRY_INTERVAL", "2"))

    @property
    def COOLDOWN_SECONDS(self) -> int:  # noqa: N802
        return self.cooldown_seconds

    @property
    def DETECTION_CONFIDENCE(self) -> float:  # noqa: N802
        return self.detection_confidence

    @property
    def DB_MAX_RETRIES(self) -> int:  # noqa: N802
        return self.db_max_retries

    @property
    def DB_RETRY_INTERVAL(self) -> int:  # noqa: N802
        return self.db_retry_interval

    # --- snapshots ---
    save_snapshots: bool = os.getenv("SAVE_SNAPSHOTS", "true").lower() in ("true", "1", "yes")
    snapshot_dir: str = os.getenv("SNAPSHOT_DIR", "./data/snapshots").strip()
    snapshot_on_unknown: bool = os.getenv("SNAPSHOT_ON_UNKNOWN", "true").lower() in ("true", "1", "yes")
    snapshot_on_low_conf: bool = os.getenv("SNAPSHOT_ON_LOW_CONF", "true").lower() in ("true", "1", "yes")
    low_conf_distance: float = float(os.getenv("LOW_CONF_DISTANCE", "0.85"))

    @property
    def SAVE_SNAPSHOTS(self) -> bool:  # noqa: N802
        return self.save_snapshots

    @property
    def SNAPSHOT_DIR(self) -> str:  # noqa: N802
        return self.snapshot_dir

    @property
    def SNAPSHOT_ON_UNKNOWN(self) -> bool:  # noqa: N802
        return self.snapshot_on_unknown

    @property
    def SNAPSHOT_ON_LOW_CONF(self) -> bool:  # noqa: N802
        return self.snapshot_on_low_conf

    @property
    def LOW_CONF_DISTANCE(self) -> float:  # noqa: N802
        return self.low_conf_distance


settings = Settings()

# ── Fail-fast validation: crash saat startup jika config kritis tidak ada ──
# Ini lebih baik dari memakai default berbahaya yang mungkin tidak disadari
_missing: list[str] = []

if not settings.secret_key:
    _missing.append("SECRET_KEY")

if not settings.database_url:
    _missing.append("DATABASE_URL")

if not settings.default_admin_user:
    _missing.append("DEFAULT_ADMIN_USER")

if not settings.default_admin_password:
    _missing.append("DEFAULT_ADMIN_PASSWORD")

if _missing:
    raise RuntimeError(
        f"Required environment variables not set: {', '.join(_missing)}\n"
        "Copy .env.production.example → .env dan isi semua nilai CHANGE_THIS."
    )
