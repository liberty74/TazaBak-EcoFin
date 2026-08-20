"""Chooses which engine judges a photograph of bread.

Two engines answer the same three-way question, and they are not equal:

* CLIP runs on this machine and returns a softmax over cosine similarities.
  It needs no network and its numbers are the model's own distribution. It is
  the engine the technical defence is built on, so it always goes first.
* Gemini answers over the network with no local memory cost. It exists for
  the free cloud instance, where 512 MB cannot hold CLIP and torch at all.

The order is deliberate: wherever the local model is installed, nothing goes
over the network — the defence stand keeps working without Wi-Fi, and the
public showcase stops being a dead button.
"""

from __future__ import annotations

import logging
from importlib.util import find_spec
from functools import lru_cache
from pathlib import Path

from app.services.clip_bread import BreadClassification, ClipAnalysisError, classify_bread
from app.services.gemini_vision import classify_bread_remote, remote_analysis_available


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def local_models_installed() -> bool:
    """Whether CLIP can run here at all.

    ``find_spec`` rather than an import: asking the question must not itself
    pull a gigabyte of weights into memory. The answer cannot change while the
    process lives, so it is computed once.
    """

    return all(
        find_spec(name) is not None for name in ("torch", "transformers")
    )


def analysis_mode() -> str:
    """How photographs are judged here: locally, remotely, or not at all."""

    if local_models_installed():
        return "local"
    if remote_analysis_available():
        return "remote"
    return "unavailable"


def classify(image_path: Path) -> BreadClassification:
    """Return one verdict, from whichever engine this machine can offer."""

    if local_models_installed():
        try:
            return classify_bread(image_path)
        except ClipAnalysisError:
            # Installed but unusable — a corrupted cache, a half-downloaded
            # weight file. Falling through beats answering 503 when a working
            # remote engine is configured.
            if not remote_analysis_available():
                raise
            logger.warning("Local classifier failed; falling back to the remote engine")

    if not remote_analysis_available():
        raise ClipAnalysisError("No bread classifier is available on this machine")

    return classify_bread_remote(image_path)
