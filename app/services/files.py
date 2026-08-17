"""Safe, size-limited image persistence."""

from __future__ import annotations

import os
import tempfile
import warnings
from hashlib import sha256
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image
from starlette.concurrency import run_in_threadpool

from app.config import settings


CHUNK_SIZE = 64 * 1024


class InvalidImageError(ValueError):
    """Raised when an uploaded file is not a supported image."""


@dataclass(frozen=True, slots=True)
class StoredImage:
    absolute_path: Path
    relative_path: str
    mime_type: str
    size_bytes: int
    sha256_hex: str

    @property
    def public_url(self) -> str:
        return f"/static/{self.relative_path}"


def _identify_image(header: bytes) -> tuple[str, str] | None:
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None


def _has_valid_envelope(
    extension: str, header: bytes, tail: bytes, size: int
) -> bool:
    """Reject obviously truncated/spoofed files without a heavyweight decoder."""

    if extension == ".jpg":
        return size >= 4 and tail.endswith(b"\xff\xd9")
    if extension == ".png":
        return size >= 20 and tail.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82")
    if extension == ".webp":
        if size < 12 or len(header) < 12:
            return False
        declared_size = int.from_bytes(header[4:8], byteorder="little") + 8
        return declared_size == size
    return False


def _validate_decoded_image(path: Path) -> None:
    """Decode metadata and reject malformed or decompression-bomb images."""

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                width, height = image.size
                if width <= 0 or height <= 0:
                    raise InvalidImageError("Image dimensions are invalid")
                if width * height > settings.max_image_pixels:
                    raise InvalidImageError(
                        f"Image exceeds the {settings.max_image_pixels}-pixel limit"
                    )
                image.verify()
    except InvalidImageError:
        raise
    except (
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise InvalidImageError("Uploaded image cannot be safely decoded") from exc


async def save_image_upload(upload: UploadFile, category: str) -> StoredImage:
    """Stream an image into static storage and atomically publish it."""

    destination_dir = settings.static_dir / category
    destination_dir.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(prefix="upload-", suffix=".tmp", dir=destination_dir)
    temporary_path = Path(temporary_name)
    size = 0
    header = bytearray()
    tail = bytearray()
    digest = sha256()

    try:
        with os.fdopen(fd, "wb") as output:
            while chunk := await upload.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise InvalidImageError(
                        f"Image exceeds the {settings.max_upload_bytes}-byte limit"
                    )
                if len(header) < 16:
                    header.extend(chunk[: 16 - len(header)])
                tail.extend(chunk)
                if len(tail) > 16:
                    del tail[:-16]
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())

        if size == 0:
            raise InvalidImageError("Uploaded image is empty")

        image_type = _identify_image(bytes(header))
        if image_type is None:
            raise InvalidImageError("Only JPEG, PNG and WebP images are supported")

        extension, canonical_mime = image_type
        if not _has_valid_envelope(extension, bytes(header), bytes(tail), size):
            raise InvalidImageError("Uploaded image is truncated or malformed")
        await run_in_threadpool(_validate_decoded_image, temporary_path)
        final_path = destination_dir / f"{uuid4().hex}{extension}"
        os.replace(temporary_path, final_path)
        relative_path = final_path.relative_to(settings.static_dir).as_posix()
        return StoredImage(
            absolute_path=final_path,
            relative_path=relative_path,
            mime_type=canonical_mime,
            size_bytes=size,
            sha256_hex=digest.hexdigest(),
        )
    finally:
        await upload.close()
        temporary_path.unlink(missing_ok=True)


def remove_stored_image(image: StoredImage) -> None:
    """Remove an upload after a failed database transaction."""

    image.absolute_path.unlink(missing_ok=True)
