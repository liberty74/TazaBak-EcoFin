

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Local development uses .env; deployment environments can still provide
# variables directly and take precedence over this file.
load_dotenv(BASE_DIR / ".env", override=False)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _normalize_origin(value: str) -> str:
    """Bring one CORS entry to the exact form a browser sends.

    Two shapes arrive here that would never match otherwise. A trailing slash
    (``https://app.example.com/``) is a classic silent failure: the ``Origin``
    header never carries one, so the entry matches nothing and the console
    only says "CORS". And a bare host arrives from managed hosting, where the
    platform substitutes a service's host name without a scheme; on such a
    platform the site is served over TLS, so ``https`` is the only sane guess.
    """

    trimmed = value.strip().rstrip("/")
    if not trimmed or "://" in trimmed:
        return trimmed
    return f"https://{trimmed}"


def _env_origins(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        origin for origin in (_normalize_origin(item) for item in _env_csv(name, default)) if origin
    )


def _normalize_database_url(value: str) -> str:
    """Pin PostgreSQL to the psycopg (v3) driver without forcing every
    deployment to spell it out in DATABASE_URL.

    SQLAlchemy defaults a bare ``postgresql://`` scheme to psycopg2, which is
    not installed here — psycopg (v3) is. Rewriting only the unqualified
    scheme keeps an already-explicit ``postgresql+psycopg://`` untouched.
    """

    if value.startswith("postgresql://") or value.startswith("postgres://"):
        return "postgresql+psycopg://" + value.split("://", 1)[1]
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Миска добра — TazaBAK API"
    app_version: str = "2.0.0"
    database_url: str = _normalize_database_url(
        os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'tazabak.db').as_posix()}")
    )
    static_dir: Path = BASE_DIR / "static"
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    max_upload_bytes: int = _env_int("MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
    max_image_pixels: int = _env_int("MAX_IMAGE_PIXELS", 16_000_000)
    seed_demo_data: bool = _env_bool("SEED_DEMO_DATA", True)
    app_env: str = os.getenv("APP_ENV", "development").casefold()
    dispatcher_api_key: str = os.getenv(
        "DISPATCHER_API_KEY", "123"
    )
    cors_origins: tuple[str, ...] = _env_origins(
        "CORS_ORIGINS",
        (
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ),
    )
    cors_origin_regex: str = os.getenv(
        "CORS_ORIGIN_REGEX",
        # Localhost and private LAN origins allow a phone on the same Wi-Fi to
        # use the development frontend without opening CORS to the internet.
        r"https?://(?:(?:localhost|127\.0\.0\.1)|(?:10(?:\.\d{1,3}){3})|(?:192\.168(?:\.\d{1,3}){2})|(?:172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}))(?::\d+)?",
    )

    # Physical calibration of the 25 cm TazaBAK municipal prototype.
    # HC-SR04 distance is measured from the lid down to the waste surface.
    h_empty_cm: float = _env_float("H_EMPTY_CM", 25.0)
    h_full_cm: float = _env_float("H_FULL_CM", 7.0)
    ema_alpha: float = _env_float("EMA_ALPHA", 0.3)
    retired_municipal_device_ids: tuple[str, ...] = _env_csv(
        "RETIRED_MUNICIPAL_DEVICE_IDS", ("municipal-rio-001",)
    )

    # FireScore remains in telemetry as diagnostic analytics only. The safety
    # interlock itself is an absolute reading from the one installed DS18B20.
    fire_weight_delta: float = _env_float("FIRE_WEIGHT_DELTA", 0.7)
    fire_weight_rate: float = _env_float("FIRE_WEIGHT_RATE", 0.3)
    fire_temperature_threshold_c: float = _env_float(
        "FIRE_TEMPERATURE_THRESHOLD_C", 50.0
    )
    min_rate_interval_seconds: float = _env_float(
        "MIN_RATE_INTERVAL_SECONDS", 1.0
    )
    websocket_send_timeout_seconds: float = _env_float(
        "WEBSOCKET_SEND_TIMEOUT_SECONDS", 2.0
    )

    # Gemini eco-assistant. The API key is intentionally environment-only.
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    gemini_fallback_models: tuple[str, ...] = _env_csv(
        "GEMINI_FALLBACK_MODELS", ("gemini-flash-latest",)
    )
    gemini_timeout_seconds: float = _env_float("GEMINI_TIMEOUT_SECONDS", 15.0)
    gemini_max_output_tokens: int = _env_int("GEMINI_MAX_OUTPUT_TOKENS", 500)

    camera_analysis_enabled: bool = _env_bool("CAMERA_ANALYSIS_ENABLED", True)
    camera_analysis_interval_seconds: float = _env_float(
        "CAMERA_ANALYSIS_INTERVAL_SECONDS", 5.0
    )
    camera_capture_timeout_seconds: float = _env_float(
        "CAMERA_CAPTURE_TIMEOUT_SECONDS", 5.0
    )
    camera_alert_cooldown_seconds: int = _env_int(
        "CAMERA_ALERT_COOLDOWN_SECONDS", 300
    )
    camera_frame_retention: int = _env_int("CAMERA_FRAME_RETENTION", 100)
    camera_illegal_dump_min_objects: int = _env_int(
        "CAMERA_ILLEGAL_DUMP_MIN_OBJECTS", 3
    )
    camera_illegal_dump_classes: tuple[str, ...] = _env_csv(
        "CAMERA_ILLEGAL_DUMP_CLASSES",
        (
            "bottle",
            "cup",
            "bowl",
            "banana",
            "apple",
            "orange",
            "sandwich",
            "backpack",
            "handbag",
            "suitcase",
        ),
    )
    # EcoFin. A collection is recognised when the measured level drops sharply
    # between two consecutive readings: a full bin becomes an empty one only
    # when the truck has actually emptied it.
    collection_drop_from_percent: float = _env_float(
        "COLLECTION_DROP_FROM_PERCENT", 45.0
    )
    collection_drop_to_percent: float = _env_float(
        "COLLECTION_DROP_TO_PERCENT", 15.0
    )

    bio_reward_points: int = _env_int("BIO_REWARD_POINTS", 15)
    nft_price_points: int = _env_int("NFT_PRICE_POINTS", 100)
    yolo_model_path: str = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    yolo_confidence: float = _env_float("YOLO_CONFIDENCE", 0.25)
    yolo_device: str = os.getenv("YOLO_DEVICE", "cpu")
    # Bread quality is decided by CLIP, not by COCO classes: the dataset
    # YOLOv8 is trained on contains neither bread nor mold.
    clip_model_name: str = os.getenv("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
    # Below this probability the photo is not judged at all and earns nothing.
    clip_min_confidence: float = _env_float("CLIP_MIN_CONFIDENCE", 0.5)

    def __post_init__(self) -> None:
        if self.h_empty_cm <= self.h_full_cm:
            raise ValueError("H_EMPTY_CM must be greater than H_FULL_CM")
        if not 0.0 < self.ema_alpha <= 1.0:
            raise ValueError("EMA_ALPHA must be in the (0, 1] interval")
        if not 0.0 < self.fire_temperature_threshold_c <= 250.0:
            raise ValueError(
                "FIRE_TEMPERATURE_THRESHOLD_C must be in the (0, 250] interval"
            )
        if self.min_rate_interval_seconds <= 0:
            raise ValueError("MIN_RATE_INTERVAL_SECONDS must be positive")
        if self.websocket_send_timeout_seconds <= 0:
            raise ValueError("WEBSOCKET_SEND_TIMEOUT_SECONDS must be positive")
        if self.gemini_timeout_seconds <= 0:
            raise ValueError("GEMINI_TIMEOUT_SECONDS must be positive")
        if self.gemini_max_output_tokens < 32:
            raise ValueError("GEMINI_MAX_OUTPUT_TOKENS must be at least 32")
        if not self.gemini_model.strip():
            raise ValueError("GEMINI_MODEL must not be empty")
        if self.max_upload_bytes <= 0:
            raise ValueError("MAX_UPLOAD_BYTES must be positive")
        if self.max_image_pixels <= 0:
            raise ValueError("MAX_IMAGE_PIXELS must be positive")
        if not self.dispatcher_api_key.strip():
            raise ValueError("DISPATCHER_API_KEY must not be empty")
        if (
            self.app_env == "production"
            and self.dispatcher_api_key in {"123", "tazabak-local-dispatcher-key"}
        ):
            raise ValueError(
                "Set a non-demo DISPATCHER_API_KEY when APP_ENV=production"
            )
        if self.bio_reward_points <= 0:
            raise ValueError("BIO_REWARD_POINTS must be positive")
        if self.nft_price_points <= 0:
            raise ValueError("NFT_PRICE_POINTS must be positive")
        if not 0.0 < self.yolo_confidence <= 1.0:
            raise ValueError("YOLO_CONFIDENCE must be in the (0, 1] interval")
        if not self.clip_model_name.strip():
            raise ValueError("CLIP_MODEL_NAME must not be empty")
        # A three-way decision is never less certain than 1/3 by construction.
        if not (1 / 3) <= self.clip_min_confidence <= 1.0:
            raise ValueError(
                "CLIP_MIN_CONFIDENCE must be in the [0.34, 1] interval"
            )
        if self.camera_analysis_interval_seconds < 1:
            raise ValueError("CAMERA_ANALYSIS_INTERVAL_SECONDS must be at least 1")
        if self.camera_capture_timeout_seconds <= 0:
            raise ValueError("CAMERA_CAPTURE_TIMEOUT_SECONDS must be positive")
        if self.camera_alert_cooldown_seconds < 0:
            raise ValueError("CAMERA_ALERT_COOLDOWN_SECONDS must not be negative")
        if self.camera_frame_retention < 1:
            raise ValueError("CAMERA_FRAME_RETENTION must be at least 1")
        if self.camera_illegal_dump_min_objects < 1:
            raise ValueError("CAMERA_ILLEGAL_DUMP_MIN_OBJECTS must be at least 1")
        if not 0.0 <= self.collection_drop_to_percent < self.collection_drop_from_percent <= 100.0:
            raise ValueError(
                "COLLECTION_DROP_TO_PERCENT must be below "
                "COLLECTION_DROP_FROM_PERCENT, both within [0, 100]"
            )


settings = Settings()
