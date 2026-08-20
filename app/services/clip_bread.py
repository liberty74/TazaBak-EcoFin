"""Zero-shot bread quality classification with CLIP.

YOLOv8 is trained on COCO, a dataset that contains neither bread nor mold.
Treating the class "broccoli" as a stand-in for mold is not a classifier — it
is a coincidence, and the first question about it breaks the answer.

CLIP places images and text in one shared vector space, so a photo can be
compared against a written description of what we are looking for. That
expresses the three decisions this project actually needs without collecting
and labelling a dataset:

    fresh bread     -> approve
    bread with mold -> reject
    no bread at all -> invalid

The comparison is a cosine similarity turned into probabilities by a softmax:

    similarity = image_vector · text_vector     (both unit length)
    logits     = similarity × exp(logit_scale)  (CLIP's own temperature)
    p          = softmax(logits)

Probabilities are reported alongside the decision, so a rejected loaf can be
argued with instead of merely accepted.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.config import settings


logger = logging.getLogger(__name__)


BreadDecision = Literal["fresh_bread", "moldy_bread", "no_bread"]

# Several phrasings per class, averaged into one direction in embedding space.
# A single sentence is a single point and is sensitive to its own wording;
# averaging a few of them costs nothing and needs no training data.
PROMPTS: dict[BreadDecision, tuple[str, ...]] = {
    "fresh_bread": (
        "a photo of fresh bread",
        "a photo of a clean dry loaf of bread",
        "a close-up photo of good edible bread",
    ),
    "moldy_bread": (
        "a photo of bread with mold",
        "a photo of moldy spoiled bread",
        "a close-up photo of bread covered in green and white fungus",
    ),
    "no_bread": (
        "a photo with no bread in it",
        "a photo of an object that is not bread",
        "a photo of an empty surface",
    ),
}


class ClipAnalysisError(RuntimeError):
    """Raised when the model cannot be loaded or inference fails."""


@dataclass(frozen=True, slots=True)
class BreadClassification:
    """One decision with the evidence that produced it."""

    decision: BreadDecision
    confidence: float
    probabilities: dict[str, float]
    model: str
    # Which method produced the numbers. CLIP computes a softmax over cosine
    # similarities; the remote engine reports its own confidence. The screen
    # names the engine so it never claims one while showing the other.
    engine: str = "clip-zero-shot"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "engine": self.engine,
            "probabilities": self.probabilities,
            "model": self.model,
        }


_model: Any | None = None
_processor: Any | None = None
_text_features: Any | None = None
_load_lock = threading.Lock()
_inference_lock = threading.Lock()


def _load() -> tuple[Any, Any, Any]:
    """Load the model once per process and embed the prompts once with it."""

    global _model, _processor, _text_features
    if _model is not None and _processor is not None and _text_features is not None:
        return _model, _processor, _text_features

    with _load_lock:
        if _model is not None and _processor is not None and _text_features is not None:
            return _model, _processor, _text_features
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            logger.info("Loading CLIP model=%s", settings.clip_model_name)
            model = CLIPModel.from_pretrained(settings.clip_model_name)
            model.eval()
            processor = CLIPProcessor.from_pretrained(settings.clip_model_name)

            # The text side never changes, so the prompts are embedded once at
            # load time rather than on every uploaded photo.
            with torch.no_grad():
                directions = []
                for phrasings in PROMPTS.values():
                    tokens = processor(
                        text=list(phrasings), return_tensors="pt", padding=True
                    )
                    embedded = model.get_text_features(**tokens)
                    embedded = embedded / embedded.norm(dim=-1, keepdim=True)
                    directions.append(embedded.mean(dim=0))
                text_features = torch.stack(directions)
                text_features = text_features / text_features.norm(
                    dim=-1, keepdim=True
                )
        except Exception as exc:
            logger.exception("Could not load CLIP model=%s", settings.clip_model_name)
            raise ClipAnalysisError("CLIP model is unavailable") from exc

        _model, _processor, _text_features = model, processor, text_features

    return _model, _processor, _text_features


def classify_bread(image_path: Path) -> BreadClassification:
    """Compare one photo against every prompt and report the probabilities."""

    model, processor, text_features = _load()

    try:
        import torch
        from PIL import Image

        with Image.open(image_path) as opened:
            image = opened.convert("RGB")

        # The model keeps mutable internal state; serialize inference per process.
        with _inference_lock, torch.no_grad():
            inputs = processor(images=image, return_tensors="pt")
            image_features = model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(
                dim=-1, keepdim=True
            )
            logits = (image_features @ text_features.T) * model.logit_scale.exp()
            scores = logits.softmax(dim=-1)[0].tolist()
    except Exception as exc:
        logger.exception("CLIP inference failed image=%s", image_path)
        raise ClipAnalysisError("CLIP inference failed") from exc

    probabilities = {
        decision: round(float(score), 4)
        for decision, score in zip(PROMPTS, scores)
    }
    decision = max(probabilities, key=probabilities.__getitem__)
    return BreadClassification(
        decision=decision,  # type: ignore[arg-type]
        confidence=probabilities[decision],
        probabilities=probabilities,
        model=settings.clip_model_name,
    )


def bread_status(
    classification: BreadClassification,
) -> tuple[str, Literal["mold_detected", "not_bread", "low_confidence"] | None]:
    """Translate a classification into the decision the application acts on.

    An unconfident answer awards nothing. Points are real value, and handing
    them out on a guess is worse than asking the resident for a better photo.
    """

    if classification.confidence < settings.clip_min_confidence:
        return "invalid", "low_confidence"
    if classification.decision == "moldy_bread":
        return "reject", "mold_detected"
    if classification.decision == "fresh_bread":
        return "approve", None
    return "invalid", "not_bread"
