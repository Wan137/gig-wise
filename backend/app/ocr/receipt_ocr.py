"""Receipt OCR: image preprocessing + Tesseract text extraction.

Preprocessing matters more than OCR engine choice for accuracy on
phone-camera photos of receipts (uneven lighting, skew, low-contrast thermal
paper). Each step is wrapped so a failure degrades to the previous, simpler
stage instead of raising - a receipt photo the preprocessing pipeline can't
handle should still get *some* OCR attempt, not a crash.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

_configured = False


def _ensure_tesseract_configured() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    _configured = True


@dataclass
class OcrResult:
    raw_text: str
    confidence: float  # 0.0-1.0, mean word-level confidence from Tesseract


class OcrError(Exception):
    """Raised when the source image can't be opened/read at all."""


def _to_grayscale(image: Image.Image) -> np.ndarray:
    cv_img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    return cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)


def _deskew(gray: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(gray < 200))
    if coords.shape[0] < 20:
        return gray  # not enough dark pixels to estimate a skew angle reliably
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5:
        return gray  # not worth the interpolation cost/risk for a near-zero skew
    height, width = gray.shape
    matrix = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
    return cv2.warpAffine(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Grayscale -> upscale small images -> denoise -> deskew -> adaptive threshold."""
    gray = _to_grayscale(image)

    # Receipts photographed at low resolution OCR poorly - Tesseract does much
    # better once characters are at least ~20-30px tall.
    height, width = gray.shape
    if width < 1000:
        scale = 1000 / width
        gray = cv2.resize(gray, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.fastNlMeansDenoising(gray, h=10)

    try:
        gray = _deskew(gray)
    except Exception:
        logger.warning("Deskew failed, continuing with the un-rotated image", exc_info=True)

    threshold = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return Image.fromarray(threshold)


def run_ocr(image_path: str) -> OcrResult:
    """Runs the full preprocess -> Tesseract pipeline against an image file."""
    _ensure_tesseract_configured()

    try:
        image = Image.open(image_path)
        image.load()
    except Exception as exc:
        raise OcrError(f"Could not open image at {image_path}: {exc}") from exc

    try:
        processed = preprocess_for_ocr(image)
    except Exception:
        logger.warning("Preprocessing failed, falling back to the raw image for OCR", exc_info=True)
        processed = image

    try:
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
        raw_text = pytesseract.image_to_string(processed).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError(
            "Tesseract is not installed or not on PATH. Set TESSERACT_CMD in .env to its executable path."
        ) from exc

    confidences = [float(c) for c, w in zip(data["conf"], data["text"]) if w.strip() and float(c) >= 0]
    mean_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

    if not raw_text:
        logger.warning("OCR produced no text for %s", image_path)

    return OcrResult(raw_text=raw_text, confidence=round(mean_confidence, 3))
