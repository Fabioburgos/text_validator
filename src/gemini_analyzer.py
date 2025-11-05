import io
import json
import logging
import os
import re
from typing import List, Dict, Optional, Any

logger = logging.getLogger("GeminiAnalyzer")
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)

# Try optional imports for real Gemini integration
try:
    from google import genai  # type: ignore
    REAL_GENAI_AVAILABLE = True
except Exception:
    genai = None  # type: ignore
    REAL_GENAI_AVAILABLE = False

# Try to import PyPDF2 to extract pages/text
try:
    from PyPDF2 import PdfReader, PdfWriter  # type: ignore
    HAS_PYPDF2 = True
except Exception:
    PdfReader = None  # type: ignore
    PdfWriter = None  # type: ignore
    HAS_PYPDF2 = False
    logger.debug("PyPDF2 not available — PDF text extraction will be limited.")


class GeminiAnalyzer:
    """
    Analyzer that can use Google GenAI (Gemini) when available, otherwise runs a local mock analysis.
    Public methods:
      - analyze_pdf_pages(pdf_input: bytes|path, start_page: int, end_page: int) -> List[Dict]
      - analyze_single_page(pdf_input: bytes|path, page_num: int) -> List[Dict]
    """

    CATEGORIAS_VALIDAS = {
        "sesgo_genero",
        "sesgo_religion",
        "sesgo_politica",
        "ortografia",
        "gramatica",
        "semantica",
    }

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_name: Optional[str] = None,
        use_real: bool = True,
    ):
        # read defaults from environment if not provided
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        self.location = location or os.environ.get("GCP_LOCATION", "us-east1")
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "models/text-bison@001")
        # enable real only if user wants and library seems available
        self.want_real = bool(use_real)
        self.real_available = REAL_GENAI_AVAILABLE and self.want_real
        self._client: Optional[Any] = None
        self._initialize_client()

    def _initialize_client(self):
        """
        Attempt to initialize a google-genai client. If anything fails, continue in mock mode.
        """
        if not self.real_available:
            logger.info("GeminiAnalyzer running in mock mode (real google-genai not available).")
            self.real_available = False
            return

        try:
            # store module ref; real calls performed in _call_gemini
            self._client = genai
            logger.info("google-genai library found; GeminiAnalyzer will attempt real calls.")
        except Exception as exc:
            logger.exception("Failed to initialize google-genai client; falling back to mock: %s", exc)
            self.real_available = False
            self._client = None

    # -------------------------
    # PDF helpers (PyPDF2)
    # -------------------------
    def _extract_single_page_pdf(self, pdf_bytes: bytes, page_num: int) -> bytes:
        if not HAS_PYPDF2:
            return pdf_bytes
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            if page_num < 1 or page_num > len(reader.pages):
                raise IndexError("page_num out of range")
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num - 1])
            out = io.BytesIO()
            writer.write(out)
            out.seek(0)
            return out.read()
        except Exception as e:
            logger.debug("extract_single_page_pdf failed: %s", e)
            return pdf_bytes

    def _read_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        if not HAS_PYPDF2:
            return ""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            if not reader.pages:
                return ""
            page = reader.pages[0]
            return (page.extract_text() or "").strip()
        except Exception as e:
            logger.debug("read_text_from_pdf_bytes failed: %s", e)
            return ""

    # -------------------------
    # Real Gemini call wrapper
    # -------------------------
    def _call_gemini(self, prompt: str, max_output_tokens: int = 512) -> Optional[str]:
        if not self.real_available or self._client is None:
            return None

        try:
            # Preferred simple helper if available
            if hasattr(self._client, "generate_text"):
                resp = self._client.generate_text(model=self.model_name, input=prompt)
                text = getattr(resp, "text", None) or getattr(resp, "output", None)
                if isinstance(text, list):
                    return text[0] if text else None
                return text
            if hasattr(self._client, "TextGenerationModel"):
                Model = getattr(self._client, "TextGenerationModel")
                model = Model.from_pretrained(self.model_name)  # type: ignore
                out = model.generate(prompt)
                if hasattr(out, "text"):
                    return out.text
                if hasattr(out, "candidates"):
                    return getattr(out.candidates[0], "content", None)
            if hasattr(self._client, "generate"):
                resp = self._client.generate(model=self.model_name, prompt=prompt)
                return getattr(resp, "output", None) or getattr(resp, "text", None)
        except Exception as e:
            logger.exception("Real Gemini call failed, falling back to mock: %s", e)
            self.real_available = False
            return None

        logger.debug("google-genai available but no known call pattern matched; falling back to mock.")
        return None

    # -------------------------
    # Mock heuristics (keeps previous behavior)
    # -------------------------
    def _mock_analyze_text(self, text: str, page_num: int) -> List[Dict]:
        findings = []
        lower = (text or "").lower()

        male_words = {"he", "him", "his", "man", "men", "boys"}
        female_words = {"she", "her", "hers", "woman", "women", "girls"}
        words = set(lower.split())
        if words & male_words and not (words & female_words):
            findings.append({
                "categoria": "sesgo_genero",
                "descripcion": "Predominio de referencias masculinas sin balance.",
                "score": 0.6
            })
        if words & female_words and not (words & male_words):
            findings.append({
                "categoria": "sesgo_genero",
                "descripcion": "Predominio de referencias femeninas sin balance.",
                "score": 0.6
            })

        religion_terms = {"religion", "christian", "muslim", "jewish", "buddhist", "church", "mosque"}
        politics_terms = {"vote", "politic", "party", "president", "congress", "senate", "policy"}
        if any(t in lower for t in religion_terms):
            findings.append({
                "categoria": "sesgo_religion",
                "descripcion": "Referencias religiosas detectadas que podrían implicar sesgo.",
                "score": 0.5
            })
        if any(t in lower for t in politics_terms):
            findings.append({
                "categoria": "sesgo_politica",
                "descripcion": "Referencias políticas detectadas.",
                "score": 0.5
            })

        if "  " in text:
            findings.append({
                "categoria": "ortografia",
                "descripcion": "Espacios dobles detectados — posible problema ortográfico/formatual.",
                "score": 0.3
            })

        sentences = [s for s in text.replace("\r", " ").split(".") if s.strip()]
        if sentences and any(s and s[0].islower() for s in sentences):
            findings.append({
                "categoria": "gramatica",
                "descripcion": "Algunas oraciones parecen comenzar en minúscula.",
                "score": 0.4
            })

        tokens = [t for t in lower.split() if t]
        if len(tokens) < 10:
            findings.append({
                "categoria": "semantica",
                "descripcion": "Contenido muy corto — posible falta de información contextual.",
                "score": 0.6
            })
        elif len(set(tokens)) < max(3, len(tokens) // 3):
            findings.append({
                "categoria": "semantica",
                "descripcion": "Contenido con mucha repetición léxica — revisar variedad semántica.",
                "score": 0.4
            })

        return findings

    def _validate_and_clean_hallazgos(self, hallazgos: List[Dict]) -> List[Dict]:
        cleaned: List[Dict] = []
        for h in hallazgos:
            cat = h.get("categoria", "")
            if cat not in self.CATEGORIAS_VALIDAS:
                cat = "semantica"
            cleaned.append({
                "categoria": cat,
                "descripcion": str(h.get("descripcion", "")).strip(),
                "score": float(h.get("score", 0.0))
            })
        return cleaned

    def _analyze_single_page(self, pdf_bytes: bytes, page_num: int) -> List[Dict]:
        text = self._read_text_from_pdf_bytes(pdf_bytes)

        # If real Gemini is available, attempt a model call with a structured prompt
        if self.real_available:
            prompt = (
                f"Analiza el siguiente texto para detectar sesgos y problemas lingüísticos. "
                f"Devuelve hallazgos en forma de lista con campos: categoria, descripcion, score (0-1).\n\nTexto (pagina {page_num}):\n{text}"
            )
            model_output = self._call_gemini(prompt)
            if model_output:
                # Best-effort: attempt to interpret model_output if it is JSON-like.
                return self._validate_and_clean_hallazgos(
                    [{"categoria": "semantica", "descripcion": model_output[:2000], "score": 0.5}]
                )
        # Mock fallback
        hallazgos = self._mock_analyze_text(text, page_num)
        return self._validate_and_clean_hallazgos(hallazgos)

    def analyze_pdf_pages(self, pdf_input: bytes, start_page: int = 1, end_page: int = 3) -> List[Dict]:
        results = []

        if isinstance(pdf_input, (bytes, bytearray)):
            if HAS_PYPDF2:
                try:
                    reader = PdfReader(io.BytesIO(pdf_input))
                    total = len(reader.pages)
                    s = max(1, start_page)
                    e = min(end_page, total)
                    if s > e:
                        return []
                    for p in range(s, e + 1):
                        page_bytes = self._extract_single_page_pdf(pdf_input, p)
                        findings = self._analyze_single_page(page_bytes, p)
                        results.append({"page": p, "findings": findings})
                    return results
                except Exception as e:
                    logger.exception("Error reading PDF bytes: %s", e)
                    findings = self._analyze_single_page(pdf_input, 1)
                    return [{"page": 1, "findings": findings}]
            else:
                findings = self._analyze_single_page(pdf_input, 1)
                return [{"page": 1, "findings": findings}]
        else:
            try:
                with open(str(pdf_input), "rb") as f:
                    data = f.read()
                return self.analyze_pdf_pages(data, start_page=start_page, end_page=end_page)
            except Exception as e:
                logger.exception("analyze_pdf_pages received unsupported input: %s", e)
                return []

    def analyze_single_page(self, pdf_input: bytes, page_num: int) -> List[Dict]:
        if isinstance(pdf_input, (bytes, bytearray)):
            page_bytes = self._extract_single_page_pdf(pdf_input, page_num)
            return self._analyze_single_page(page_bytes, page_num)
        else:
            try:
                with open(str(pdf_input), "rb") as f:
                    data = f.read()
                page_bytes = self._extract_single_page_pdf(data, page_num)
                return self._analyze_single_page(page_bytes, page_num)
            except Exception as e:
                logger.exception("analyze_single_page error: %s", e)
                return []