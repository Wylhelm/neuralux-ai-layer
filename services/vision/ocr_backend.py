"""OCR backend with PaddleOCR primary and Tesseract fallback.

Provides a simple interface:
- OCRProcessor.run(image: PIL.Image.Image, language: Optional[str]) -> dict

Returns dict with keys: text (str), confidence (float), words (List[str]).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import importlib

from PIL import Image


class OCRProcessor:
    """High-level OCR processor with lazy-loaded engines."""

    def __init__(self) -> None:
        self._paddleocr = None
        self._paddle_engine = None
        self._pytesseract = None

    def _ensure_paddle(self, language: Optional[str]) -> bool:
        if self._paddleocr is None:
            try:
                self._paddleocr = importlib.import_module("paddleocr")
            except Exception:
                self._paddleocr = False
                return False
        if self._paddleocr is False:
            return False
        if self._paddle_engine is None:
            try:
                # Use English by default; allow multi-language codes like 'en' or 'en+fr'
                lang = (language or "en").split("_")[0]
                self._paddle_engine = self._paddleocr.PaddleOCR(
                    use_angle_cls=True,
                    lang=lang,
                    show_log=False,
                )
            except Exception:
                self._paddle_engine = False
                return False
        return self._paddle_engine not in (None, False)

    def _ensure_tesseract(self) -> bool:
        if self._pytesseract is None:
            try:
                self._pytesseract = importlib.import_module("pytesseract")
            except Exception:
                self._pytesseract = False
                return False
        return self._pytesseract is not False

    def run(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """Run OCR on a PIL image with PaddleOCR primary, Tesseract fallback."""
        # Normalize image to RGB
        try:
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
        except Exception:
            pass

        # Try PaddleOCR
        if self._ensure_paddle(language):
            try:
                # PaddleOCR expects numpy array (BGR) or path; convert appropriately
                import numpy as np  # type: ignore

                np_img = np.array(image)
                # Convert RGB -> BGR
                np_img = np_img[:, :, ::-1]
                result = self._paddle_engine.ocr(np_img, cls=True)
                # result is a list per image; we passed one image
                lines: List[str] = []
                words: List[str] = []
                confidences: List[float] = []
                for line in result or []:
                    # line is list of [ [box], [text, conf] ]
                    for _box, (text, conf) in line:
                        if text:
                            words.extend(text.split())
                            lines.append(text)
                        try:
                            confidences.append(float(conf))
                        except Exception:
                            pass
                joined = "\n".join(lines).strip()
                avg_conf = float(sum(confidences) / max(len(confidences), 1)) if confidences else None
                return {
                    "text": joined,
                    "confidence": avg_conf,
                    "words": words or None,
                    "engine": "paddleocr",
                }
            except Exception:
                # Fall through to Tesseract
                pass

        # Fallback: Tesseract
        if self._ensure_tesseract():
            try:
                tess: Any = self._pytesseract
                lang = (language or "eng")
                try:
                    data = tess.image_to_data(image, lang=lang, output_type=tess.Output.DICT)
                except Exception:
                    # Some builds lack Output.DICT; fallback to plain string
                    text = tess.image_to_string(image, lang=lang) or ""
                    return {
                        "text": text.strip(),
                        "confidence": None,
                        "words": text.split() or None,
                        "engine": "tesseract",
                    }
                words: List[str] = []
                confs: List[float] = []
                lines: List[str] = []
                current_line = -1
                line_buf: List[str] = []
                n = len(data.get("text", []))
                for i in range(n):
                    try:
                        txt = (data["text"][i] or "").strip()
                        if not txt:
                            continue
                        words.append(txt)
                        # group by line number if available
                        ln = int(data.get("line_num", [0])[i]) if "line_num" in data else i
                        if ln != current_line:
                            if line_buf:
                                lines.append(" ".join(line_buf))
                                line_buf = []
                            current_line = ln
                        line_buf.append(txt)
                        c_str = data.get("conf", ["-1"]) [i]
                        try:
                            c = float(c_str) if c_str not in ("-1", "-1.0", "--") else None
                            if c is not None:
                                confs.append(c)
                        except Exception:
                            pass
                    except Exception:
                        pass
                if line_buf:
                    lines.append(" ".join(line_buf))
                joined = "\n".join(lines).strip() if lines else " ".join(words)
                avg_conf = float(sum(confs) / max(len(confs), 1)) if confs else None
                return {
                    "text": joined,
                    "confidence": avg_conf,
                    "words": words or None,
                    "engine": "tesseract",
                }
            except Exception:
                pass

        # No engine available
        return {
            "text": "",
            "confidence": None,
            "words": None,
            "engine": None,
            "error": "No OCR engine available (install paddleocr or tesseract)",
        }


