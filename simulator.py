"""Telemetry and bread-sharing simulator for TazaBAK devices.

The simulator repeatedly sends a complete scenario consisting of the phases
``normal -> heating -> fire -> cooldown``.  The fire phase deliberately
contains internal DS18B20 readings above 50 degrees Celsius, which triggers
the direct municipal fire interlock. The distance values match the 25 cm
prototype bin: 25 cm is empty and 7 cm is full. After every sensor scenario it
also runs the TazaBAK-Bio flow unless explicitly disabled.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import mimetypes
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import quote
from uuid import uuid4

import requests


LOGGER = logging.getLogger("tazabak.simulator")
INGEST_PATH = "/api/sensors/ingest"
BIO_ANALYZE_PATH = "/api/bio/analyze"
USERS_PATH = "/api/users"

# The embedded PNG keeps the HTTP smoke test self-contained, but it contains no
# recognizable object and will normally produce ``status=invalid`` in YOLO.
# Supply --bread-image with a real photograph to exercise object detection.
EMBEDDED_BREAD_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@dataclass(frozen=True, slots=True)
class PhaseProfile:
    """Target sensor values for one scenario phase."""

    name: str
    temperatures_in: tuple[float, ...]
    distances: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.temperatures_in) != len(self.distances):
            raise ValueError("temperatures_in and distances must have equal lengths")


@dataclass(frozen=True, slots=True)
class TelemetrySample:
    phase: str
    distance: float
    temp_in: float
    temp_out: float

    def as_payload(self, device_id: str) -> dict[str, str | float]:
        return {
            "device_id": device_id,
            "distance": self.distance,
            "temp_in": self.temp_in,
            "temp_out": self.temp_out,
            "measured_at": datetime.now(timezone.utc).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SimulatorConfig:
    endpoint: str
    device_id: str
    bio_device_id: str
    interval: float
    timeout: float
    cycles: int
    once: bool
    seed: int | None
    base_url: str
    user_id: str
    bread_image: Path | None
    skip_bio: bool
    bio_attempts: int


@dataclass(frozen=True, slots=True)
class BreadImage:
    filename: str
    content_type: str
    data: bytes


PHASES: tuple[PhaseProfile, ...] = (
    PhaseProfile(
        name="normal",
        temperatures_in=(21.0, 21.8, 22.5, 23.0),
        distances=(25.0, 24.0, 23.0, 22.0),
    ),
    PhaseProfile(
        name="heating",
        temperatures_in=(28.0, 35.0, 43.0, 49.0),
        distances=(20.0, 17.0, 14.0, 11.0),
    ),
    PhaseProfile(
        name="fire",
        temperatures_in=(51.0, 55.0, 58.0),
        distances=(10.0, 8.0, 7.0),
    ),
    PhaseProfile(
        name="cooldown",
        temperatures_in=(47.0, 39.0, 30.0, 24.0),
        distances=(8.0, 12.0, 18.0, 23.0),
    ),
)


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def _positive_int(value: str) -> int:
    parsed = _non_negative_int(value)
    if parsed == 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _optional_int(value: str) -> int | None:
    if value.strip().lower() in {"", "none", "random"}:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer or 'random'") from exc


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Send simulated TazaBAK telemetry in normal, heating, fire, and "
            "cooldown phases, then exercise the bread-analysis flow. "
            "Command-line options override TAZABAK_* variables."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("TAZABAK_BASE_URL", "http://127.0.0.1:8000"),
        help="FastAPI base URL (env: TAZABAK_BASE_URL)",
    )
    parser.add_argument(
        "--device-id",
        default=os.getenv("TAZABAK_DEVICE_ID", "municipal-simulator-001"),
        help="Simulated device identifier (env: TAZABAK_DEVICE_ID)",
    )
    parser.add_argument(
        "--bio-device-id",
        default=os.getenv("TAZABAK_BIO_DEVICE_ID", "bio-central-park-001"),
        help="Bread-sharing box identifier (env: TAZABAK_BIO_DEVICE_ID)",
    )
    parser.add_argument(
        "--interval",
        type=_non_negative_float,
        default=os.getenv("TAZABAK_INTERVAL", "2.0"),
        metavar="SECONDS",
        help="Delay between samples; zero disables the delay (env: TAZABAK_INTERVAL)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=os.getenv("TAZABAK_TIMEOUT", "120.0"),
        metavar="SECONDS",
        help=(
            "HTTP request timeout; the first YOLO model load may be slow "
            "(env: TAZABAK_TIMEOUT)"
        ),
    )

    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument(
        "--once",
        action="store_true",
        help="Send one normal telemetry sample, run one bio flow, and exit",
    )
    run_mode.add_argument(
        "--cycles",
        type=_non_negative_int,
        default=os.getenv("TAZABAK_CYCLES", "0"),
        metavar="N",
        help=(
            "Number of complete phase scenarios; 0 runs until interrupted "
            "(env: TAZABAK_CYCLES)"
        ),
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("TAZABAK_USER_ID", "123"),
        help="User credited for approved bread (env: TAZABAK_USER_ID)",
    )
    parser.add_argument(
        "--bread-image",
        default=os.getenv("TAZABAK_BREAD_IMAGE") or None,
        metavar="PATH",
        help=(
            "JPEG, PNG, or WebP image for real YOLO inference; the embedded "
            "1x1 PNG only tests multipart transport and normally returns "
            "invalid (env: TAZABAK_BREAD_IMAGE)"
        ),
    )
    parser.add_argument(
        "--skip-bio",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("TAZABAK_SKIP_BIO"),
        help="Disable the bio flow after sensor cycles (env: TAZABAK_SKIP_BIO)",
    )
    parser.add_argument(
        "--bio-attempts",
        type=_positive_int,
        default=os.getenv("TAZABAK_BIO_ATTEMPTS", "3"),
        metavar="N",
        help=(
            "Maximum request attempts after transport/unexpected errors "
            "(env: TAZABAK_BIO_ATTEMPTS)"
        ),
    )
    parser.add_argument(
        "--seed",
        type=_optional_int,
        default=os.getenv("TAZABAK_SEED", "random"),
        help="Random seed for reproducible values (env: TAZABAK_SEED)",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default=os.getenv("TAZABAK_LOG_LEVEL", "INFO").upper(),
        help="Logging verbosity (env: TAZABAK_LOG_LEVEL)",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def normalize_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ValueError("base URL must not be empty")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("base URL must start with http:// or https://")
    return normalized


def iter_scenario(rng: random.Random) -> Iterator[TelemetrySample]:
    """Yield one full normal-to-cooldown sensor scenario."""

    ambient = rng.uniform(17.0, 25.0)
    for phase in PHASES:
        for target_temperature, target_distance in zip(
            phase.temperatures_in, phase.distances
        ):
            ambient = min(28.0, max(12.0, ambient + rng.uniform(-0.15, 0.15)))
            temp_in = target_temperature + rng.uniform(-0.25, 0.25)
            if phase.name == "fire":
                # Preserve the trigger invariant despite random sensor noise.
                temp_in = max(50.1, temp_in)

            yield TelemetrySample(
                phase=phase.name,
                distance=round(
                    min(25.0, max(7.0, target_distance + rng.uniform(-0.35, 0.35))),
                    2,
                ),
                temp_in=round(temp_in, 2),
                temp_out=round(ambient, 2),
            )


def load_bread_image(path: Path | None) -> BreadImage:
    if path is None:
        return BreadImage(
            filename="simulated-bread.png",
            content_type="image/png",
            data=EMBEDDED_BREAD_PNG,
        )

    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"could not read bread image {path}: {exc}") from exc
    if not data:
        raise ValueError(f"bread image is empty: {path}")

    guessed_type, _ = mimetypes.guess_type(path.name)
    content_type = (
        guessed_type
        if guessed_type in {"image/jpeg", "image/png", "image/webp"}
        else "application/octet-stream"
    )
    return BreadImage(
        filename=path.name,
        content_type=content_type,
        data=data,
    )


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "TazaBAK-Simulator/1.0",
        }
    )
    return session


def decode_json_response(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text[:1_000]}


def extract_balance(payload: Any) -> int | float | str | None:
    """Extract a balance from common user-response shapes for readable logs."""

    if not isinstance(payload, dict):
        return None
    for key in ("balance", "points", "points_balance", "eco_points"):
        value = payload.get(key)
        if isinstance(value, (int, float, str)) and not isinstance(value, bool):
            return value
    for key in ("user", "wallet"):
        nested = payload.get(key)
        balance = extract_balance(nested)
        if balance is not None:
            return balance
    return None


def numeric_balance(payload: Any) -> int | None:
    """Return an integer balance when the profile response contains one."""

    value = extract_balance(payload)
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def fetch_user_state(
    session: requests.Session,
    config: SimulatorConfig,
    stage: str,
) -> Any:
    user_url = f"{config.base_url}{USERS_PATH}/{quote(config.user_id, safe='')}"
    response = session.get(user_url, timeout=config.timeout)
    try:
        response.raise_for_status()
    except requests.HTTPError:
        LOGGER.error(
            "User lookup failed: stage=%s user=%s status=%s body=%r",
            stage,
            config.user_id,
            response.status_code,
            response.text[:1_000],
        )
        raise

    result = decode_json_response(response)
    balance = extract_balance(result)
    LOGGER.info(
        "User balance: stage=%s user=%s balance=%s response=%s",
        stage,
        config.user_id,
        balance if balance is not None else "unknown",
        json.dumps(result, ensure_ascii=False, default=str),
    )
    return result


def send_bio_analysis(
    session: requests.Session,
    config: SimulatorConfig,
    bread_image: BreadImage,
    attempt: int,
    operation_id: str,
) -> Any:
    bio_url = f"{config.base_url}{BIO_ANALYZE_PATH}"
    LOGGER.info(
        "Uploading bread image: attempt=%d/%d device=%s user=%s file=%s bytes=%d",
        attempt,
        config.bio_attempts,
        config.bio_device_id,
        config.user_id,
        bread_image.filename,
        len(bread_image.data),
    )
    response = session.post(
        bio_url,
        data={
            "device_id": config.bio_device_id,
            "user_id": config.user_id,
            "idempotency_key": operation_id,
        },
        files={
            "file": (
                bread_image.filename,
                bread_image.data,
                bread_image.content_type,
            )
        },
        timeout=config.timeout,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        LOGGER.error(
            "Bread analysis failed: attempt=%d status=%s body=%r",
            attempt,
            response.status_code,
            response.text[:1_000],
        )
        raise

    result = decode_json_response(response)
    LOGGER.info(
        "Bread analysis response: attempt=%d status=%s response=%s",
        attempt,
        response.status_code,
        json.dumps(result, ensure_ascii=False, default=str),
    )
    return result


def run_bio_flow(
    session: requests.Session,
    config: SimulatorConfig,
    bread_image: BreadImage,
) -> tuple[str, bool]:
    """Run the YOLO Bio request and validate its points contract.

    The returned status is one of ``approve``, ``reject``, ``invalid`` or
    ``error``.  Reject and invalid are legitimate model outcomes; ``contract_ok``
    only becomes false for transport errors or an inconsistent points result.
    """

    LOGGER.info("Starting bio flow for user=%s", config.user_id)
    before_state: Any = None
    try:
        before_state = fetch_user_state(session, config, "before")
    except requests.RequestException as exc:
        # Keep the sensor demo observable even if the configured profile is
        # temporarily unavailable; the Bio request itself will report 404.
        LOGGER.warning(
            "Could not read balance before analysis: user=%s error=%s",
            config.user_id,
            exc,
        )

    final_status = "error"
    contract_ok = True
    points_awarded = 0
    operation_id = uuid4().hex
    for attempt in range(1, config.bio_attempts + 1):
        try:
            result = send_bio_analysis(
                session, config, bread_image, attempt, operation_id
            )
        except requests.RequestException as exc:
            LOGGER.error(
                "Bread analysis request error: attempt=%d/%d error=%s",
                attempt,
                config.bio_attempts,
                exc,
            )
            continue

        status = result.get("status") if isinstance(result, dict) else None
        normalized_status = status.lower() if isinstance(status, str) else ""
        raw_points = result.get("points_awarded", 0) if isinstance(result, dict) else 0
        try:
            points_awarded = int(raw_points)
        except (TypeError, ValueError):
            points_awarded = -1

        if normalized_status == "approve":
            final_status = "approve"
            LOGGER.info(
                "Bio result: status=approve attempt=%d points_awarded=%s "
                "qr_code=%s",
                attempt,
                raw_points,
                result.get("qr_code", "unknown"),
            )
            if points_awarded != 15:
                contract_ok = False
                LOGGER.error(
                    "Bio contract violation: approve must award exactly 15 "
                    "points, received=%s",
                    raw_points,
                )
            break

        if normalized_status == "reject":
            final_status = "reject"
            LOGGER.warning(
                "Bio result: status=reject attempt=%d reason=%s points_awarded=%s "
                "qr_code=%s",
                attempt,
                result.get("reason", "mold_detected"),
                raw_points,
                result.get("qr_code", "unknown"),
            )
            if points_awarded != 0:
                contract_ok = False
                LOGGER.error("Bio contract violation: reject must award 0 points")
            break

        if normalized_status == "invalid":
            final_status = "invalid"
            LOGGER.info(
                "Bio result: status=invalid attempt=%d reason=%s "
                "points_awarded=%s qr_code=%s. This is expected for the "
                "embedded 1x1 PNG; pass --bread-image for real YOLO inference.",
                attempt,
                result.get("reason", "not_bread"),
                raw_points,
                result.get("qr_code", "unknown"),
            )
            if points_awarded != 0:
                contract_ok = False
                LOGGER.error("Bio contract violation: invalid must award 0 points")
            break

        LOGGER.warning(
            "Unexpected Bio response: attempt=%d/%d status=%r",
            attempt,
            config.bio_attempts,
            status,
        )

    after_state: Any = None
    try:
        after_state = fetch_user_state(session, config, "after")
    except requests.RequestException as exc:
        LOGGER.warning(
            "Could not read balance after analysis: user=%s error=%s",
            config.user_id,
            exc,
        )

    before_balance = numeric_balance(before_state)
    after_balance = numeric_balance(after_state)
    if before_balance is not None and after_balance is not None:
        expected_delta = 15 if final_status == "approve" else 0
        actual_delta = after_balance - before_balance
        if actual_delta != expected_delta:
            contract_ok = False
            LOGGER.error(
                "Balance contract violation: status=%s expected_delta=%d "
                "actual_delta=%d",
                final_status,
                expected_delta,
                actual_delta,
            )
        else:
            LOGGER.info(
                "Balance check passed: status=%s delta=%d balance=%d",
                final_status,
                actual_delta,
                after_balance,
            )

    if final_status == "error":
        contract_ok = False
        LOGGER.error("Bio flow ended without a recognized response")

    return final_status, contract_ok


def send_sample(
    session: requests.Session,
    config: SimulatorConfig,
    sample: TelemetrySample,
) -> Any:
    payload = sample.as_payload(config.device_id)
    LOGGER.info(
        "Sending sample: phase=%s device=%s distance=%.2fcm "
        "temp_in=%.2fC temp_out=%.2fC delta=%.2fC",
        sample.phase,
        config.device_id,
        sample.distance,
        sample.temp_in,
        sample.temp_out,
        sample.temp_in - sample.temp_out,
    )

    response = session.post(
        config.endpoint,
        json=payload,
        timeout=config.timeout,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        LOGGER.error(
            "Backend rejected telemetry: status=%s body=%r",
            response.status_code,
            response.text[:1_000],
        )
        raise

    result = decode_json_response(response)

    LOGGER.info(
        "Telemetry accepted: status=%s response=%s",
        response.status_code,
        json.dumps(result, ensure_ascii=False, default=str),
    )
    return result


def run_simulation(config: SimulatorConfig) -> int:
    rng = random.Random(config.seed)
    sent = 0
    failed = 0
    completed_cycles = 0
    bio_flows = 0
    bio_status_counts = {"approve": 0, "reject": 0, "invalid": 0, "error": 0}
    bio_contract_failures = 0
    bread_image = (
        None if config.skip_bio else load_bread_image(config.bread_image)
    )
    run_mode = (
        "once"
        if config.once
        else (f"{config.cycles} cycles" if config.cycles else "continuous")
    )
    bio_mode = (
        "disabled"
        if config.skip_bio
        else f"enabled ({config.bio_attempts} attempts)"
    )

    LOGGER.info(
        "Simulator started: endpoint=%s device=%s bio_device=%s interval=%.2fs "
        "timeout=%.2fs mode=%s seed=%s bio=%s user=%s",
        config.endpoint,
        config.device_id,
        config.bio_device_id,
        config.interval,
        config.timeout,
        run_mode,
        config.seed if config.seed is not None else "random",
        bio_mode,
        config.user_id,
    )

    with create_session() as session:
        try:
            if config.once:
                samples: Sequence[TelemetrySample] = (next(iter_scenario(rng)),)
                cycle_limit = 1
            else:
                samples = ()
                cycle_limit = config.cycles

            while config.once or cycle_limit == 0 or completed_cycles < cycle_limit:
                cycle_number = completed_cycles + 1
                cycle_samples = samples if config.once else tuple(iter_scenario(rng))
                LOGGER.info("Starting scenario cycle %d", cycle_number)

                for sample_index, sample in enumerate(cycle_samples, start=1):
                    try:
                        send_sample(session, config, sample)
                    except requests.RequestException as exc:
                        failed += 1
                        LOGGER.error(
                            "Telemetry request failed: phase=%s error=%s",
                            sample.phase,
                            exc,
                        )
                    else:
                        sent += 1

                    is_last_sample = sample_index == len(cycle_samples)
                    if config.interval > 0 and not is_last_sample:
                        time.sleep(config.interval)

                completed_cycles += 1
                LOGGER.info(
                    "Scenario cycle %d completed: accepted=%d failed=%d",
                    cycle_number,
                    sent,
                    failed,
                )

                if bread_image is not None:
                    bio_flows += 1
                    bio_status, contract_ok = run_bio_flow(
                        session, config, bread_image
                    )
                    bio_status_counts[bio_status] = (
                        bio_status_counts.get(bio_status, 0) + 1
                    )
                    if not contract_ok:
                        bio_contract_failures += 1

                if config.once:
                    break

                has_more_cycles = cycle_limit == 0 or completed_cycles < cycle_limit
                if config.interval > 0 and has_more_cycles:
                    time.sleep(config.interval)
        except KeyboardInterrupt:
            LOGGER.info("Ctrl+C received; stopping simulator gracefully")

    LOGGER.info(
        "Simulator stopped: completed_cycles=%d accepted=%d failed=%d "
        "bio_flows=%d bio_approve=%d bio_reject=%d bio_invalid=%d "
        "bio_error=%d bio_contract_failures=%d",
        completed_cycles,
        sent,
        failed,
        bio_flows,
        bio_status_counts["approve"],
        bio_status_counts["reject"],
        bio_status_counts["invalid"],
        bio_status_counts["error"],
        bio_contract_failures,
    )
    # ``reject`` and ``invalid`` are valid YOLO business outcomes, not simulator
    # failures.  Only HTTP/contract errors affect the process exit code.
    return 1 if failed or bio_contract_failures else 0


def parse_config(argv: Sequence[str] | None = None) -> tuple[SimulatorConfig, str]:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        base_url = normalize_base_url(args.base_url)
    except ValueError as exc:
        parser.error(str(exc))

    device_id = args.device_id.strip()
    if not device_id:
        parser.error("device ID must not be empty")
    bio_device_id = args.bio_device_id.strip()
    if not bio_device_id:
        parser.error("bio device ID must not be empty")

    user_id = args.user_id.strip()
    if not user_id:
        parser.error("user ID must not be empty")
    if len(user_id) > 64:
        parser.error("user ID must not exceed 64 characters")

    bread_image: Path | None = None
    if args.bread_image:
        bread_image = Path(args.bread_image).expanduser()
        if not args.skip_bio and not bread_image.is_file():
            parser.error(f"bread image does not exist or is not a file: {bread_image}")

    return (
        SimulatorConfig(
            endpoint=f"{base_url}{INGEST_PATH}",
            device_id=device_id,
            bio_device_id=bio_device_id,
            interval=args.interval,
            timeout=args.timeout,
            cycles=args.cycles,
            once=args.once,
            seed=args.seed,
            base_url=base_url,
            user_id=user_id,
            bread_image=bread_image,
            skip_bio=args.skip_bio,
            bio_attempts=args.bio_attempts,
        ),
        args.log_level,
    )


def main(argv: Sequence[str] | None = None) -> int:
    config, log_level = parse_config(argv)
    configure_logging(log_level)
    try:
        return run_simulation(config)
    except Exception:
        LOGGER.exception("Simulator terminated because of an unexpected error")
        return 2


if __name__ == "__main__":
    sys.exit(main())
