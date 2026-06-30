from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pytesseract
from PIL import Image, ImageOps


class OCRService:
    def __init__(self, tesseract_cmd: str | None = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def preprocess(self, image: Image.Image) -> Image.Image:
        gray = ImageOps.grayscale(image)
        arr = np.array(gray)
        thresh = (arr > 165) * 255
        bw = Image.fromarray(np.uint8(thresh), mode="L")
        return self._deskew(bw)

    def _deskew(self, image: Image.Image) -> Image.Image:
        arr = np.array(image)
        coords = np.column_stack(np.where(arr < 255))
        if coords.size == 0:
            return image
        angle = self._estimate_angle(coords)
        if math.isclose(angle, 0.0, abs_tol=0.1):
            return image
        return image.rotate(angle, expand=True, fillcolor=255)

    def _estimate_angle(self, coords: np.ndarray) -> float:
        centered = coords - coords.mean(axis=0)
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
        principal = vt[0]
        angle = math.degrees(math.atan2(principal[0], principal[1]))
        return max(min(angle, 45), -45)

    def extract_text_per_page(self, pages: Iterable[Image.Image]) -> list[str]:
        results: list[str] = []
        for page in pages:
            cleaned = self.preprocess(page)
            text = pytesseract.image_to_string(cleaned, lang="eng", config="--psm 6")
            results.append(text.strip())
        return results
