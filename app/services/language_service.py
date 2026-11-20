"""Language detection and multilingual metadata service for DocuMind."""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.utils.logging import logger

# Supported language codes and names
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
    "ru": "Russian",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "id": "Indonesian",
    "tr": "Turkish",
    "ur": "Urdu",
}

# Tested and primary supported languages
TESTED_LANGUAGES = {"en", "hi", "bn", "es", "fr", "de", "ar", "zh", "ru", "ja"}

# Distinctive Unicode Script ranges
SCRIPT_RANGES = [
    ("Devanagari", 0x0900, 0x097F, "hi"),
    ("Bengali", 0x0980, 0x09FF, "bn"),
    ("Arabic", 0x0600, 0x06FF, "ar"),
    ("Arabic_Ext_A", 0x0750, 0x077F, "ar"),
    ("Arabic_Ext_B", 0x08A0, 0x08FF, "ar"),
    ("Cyrillic", 0x0400, 0x04FF, "ru"),
    ("Hangul", 0xAC00, 0xD7AF, "ko"),
    ("Hangul_Jamo", 0x1100, 0x11FF, "ko"),
    ("Hiragana", 0x3040, 0x309F, "ja"),
    ("Katakana", 0x30A0, 0x30FF, "ja"),
    ("Han", 0x4E00, 0x9FFF, "zh"),  # Hanzi/Kanji (checked after Japanese kana)
]

# Urdu-specific characters within Arabic script
URDU_SPECIFIC_CHARS = set("ٹڈڑںےھچھپچژگ")

# Distinctive stopword profiles for Latin-script languages
LATIN_STOPWORDS: Dict[str, set] = {
    "en": {
        "the", "and", "is", "of", "in", "to", "for", "with", "that", "this", "on", "from",
        "by", "at", "as", "are", "was", "were", "be", "have", "has", "had", "which", "report",
        "company", "revenue", "profit", "year", "total", "financial", "growth", "cost"
    },
    "es": {
        "el", "la", "de", "en", "y", "los", "las", "un", "una", "por", "con", "del", "para",
        "es", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "fue", "este",
        "informe", "empresa", "ingresos", "beneficio", "año", "total", "financiero"
    },
    "fr": {
        "le", "la", "les", "de", "des", "en", "un", "une", "du", "dans", "pour", "avec", "sur",
        "est", "qui", "ce", "ces", "par", "au", "aux", "son", "sa", "ses", "ou", "nous",
        "rapport", "société", "chiffre", "bénéfice", "exercice", "total", "financier"
    },
    "de": {
        "der", "die", "das", "und", "in", "von", "mit", "für", "den", "ein", "eine", "auf",
        "ist", "im", "dem", "nicht", "zu", "des", "sich", "auch", "als", "nach", "wie",
        "bericht", "gesellschaft", "umsatz", "gewinn", "jahr", "gesamt", "finanzen"
    },
    "it": {
        "il", "la", "di", "in", "che", "per", "un", "una", "con", "sono", "del", "della",
        "delle", "dei", "ed", "al", "alla", "da", "ha", "questo", "questa", "anche",
        "relazione", "società", "ricavi", "utile", "anno", "totale", "finanziario"
    },
    "pt": {
        "o", "a", "de", "em", "para", "com", "não", "um", "uma", "os", "as", "do", "da",
        "dos", "das", "no", "na", "nos", "nas", "por", "mais", "como", "mas", "foi",
        "relatório", "empresa", "receita", "lucro", "ano", "total", "financeiro"
    },
    "nl": {
        "de", "het", "en", "van", "in", "een", "op", "te", "met", "voor", "zijn", "is",
        "er", "maar", "om", "ook", "dan", "over", "aan", "niet", "door", "deze", "als",
        "verslag", "bedrijf", "omzet", "winst", "jaar", "totaal", "financieel"
    },
    "id": {
        "yang", "dan", "di", "dari", "ini", "untuk", "pada", "dengan", "adalah", "ke",
        "oleh", "dalam", "bisa", "tidak", "akan", "juga", "atau", "sudah", "kami",
        "laporan", "perusahaan", "pendapatan", "laba", "tahun", "total", "keuangan"
    },
    "tr": {
        "ve", "bir", "bu", "için", "ile", "de", "da", "çok", "olan", "olarak", "en",
        "gibi", "daha", "kadar", "ise", "her", "ama", "sonra", "ancak", "ya",
        "rapor", "şirket", "gelir", "kar", "yıl", "toplam", "finansal"
    },
}


@dataclass
class LanguageDetectionResult:
    """Detailed result of language detection on a document or text passage."""
    primary_language: str
    language_code: str
    confidence: float
    additional_languages: List[str] = field(default_factory=list)
    is_mixed: bool = False
    warning: Optional[str] = None
    char_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def language_name(self) -> str:
        return self.primary_language


class LanguageDetector:
    """Robust, multi-tier language detector with zero mandatory external API dependencies."""

    def __init__(self):
        self._cache: Dict[str, LanguageDetectionResult] = {}

    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        """Returns the language codes exposed by the public configuration endpoint."""
        return dict(SUPPORTED_LANGUAGES)

    def detect(self, text: str) -> LanguageDetectionResult:
        """Detects language of input text with multi-tier heuristic and script analysis."""
        clean_text = text.strip()
        if not clean_text:
            return LanguageDetectionResult(
                primary_language="English",
                language_code="en",
                confidence=1.0,
                warning="Empty text; defaulted to English."
            )

        # Fast cache lookup for exact strings or large texts based on prefix/hash
        cache_key = f"{len(clean_text)}_{hash(clean_text[:500])}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        res = self._detect_internal(clean_text)
        if len(self._cache) < 2000:
            self._cache[cache_key] = res
        return res

    def _detect_internal(self, text: str) -> LanguageDetectionResult:
        # Sample up to 6000 characters for analysis to keep detection lightning-fast
        sample = text[:6000]

        # 1. Script-based character distribution
        script_counts: Dict[str, int] = {}
        total_meaningful_chars = 0

        for char in sample:
            if char.isspace() or char.isdigit() or unicodedata.category(char).startswith("P"):
                continue
            total_meaningful_chars += 1
            code = ord(char)
            matched = False
            for script_name, start, end, lang_code in SCRIPT_RANGES:
                if start <= code <= end:
                    script_counts[lang_code] = script_counts.get(lang_code, 0) + 1
                    matched = True
                    break
            if not matched and ('a' <= char.lower() <= 'z' or ord(char) > 0x00C0 and ord(char) <= 0x024F):
                script_counts["latin"] = script_counts.get("latin", 0) + 1

        if total_meaningful_chars == 0:
            return LanguageDetectionResult(
                primary_language="English",
                language_code="en",
                confidence=0.5,
                warning="Text contains mostly numbers or punctuation."
            )

        # Check non-Latin dominant scripts first
        non_latin_scripts = {k: v for k, v in script_counts.items() if k != "latin"}
        if non_latin_scripts:
            dominant_non_latin, highest_count = max(non_latin_scripts.items(), key=lambda x: x[1])
            ratio = highest_count / total_meaningful_chars

            if ratio >= 0.20:
                # Handle Japanese vs Chinese (Japanese contains Kana, Chinese doesn't)
                if dominant_non_latin == "zh":
                    kana_count = script_counts.get("ja", 0)
                    if kana_count > 0:
                        dominant_non_latin = "ja"

                # Handle Arabic vs Urdu
                if dominant_non_latin == "ar":
                    has_urdu = any(ch in URDU_SPECIFIC_CHARS for ch in sample)
                    if has_urdu:
                        dominant_non_latin = "ur"

                conf = round(min(0.99, ratio + 0.25), 2)
                additional = []
                is_mixed = False

                latin_ratio = script_counts.get("latin", 0) / total_meaningful_chars
                if latin_ratio >= 0.15:
                    additional.append("en")
                    is_mixed = True

                warning = None
                if conf < 0.60:
                    warning = f"Language detection confidence is moderate ({conf:.0%})."

                return LanguageDetectionResult(
                    primary_language=SUPPORTED_LANGUAGES.get(dominant_non_latin, dominant_non_latin.title()),
                    language_code=dominant_non_latin,
                    confidence=conf,
                    additional_languages=additional,
                    is_mixed=is_mixed,
                    warning=warning,
                    char_counts=script_counts
                )

        # 2. Latin script language analysis via Stopword & Vocabulary Scoring
        tokens = [w.lower() for w in re.findall(r"\b[A-Za-zÀ-ÿ]{2,}\b", sample)]
        if not tokens:
            return LanguageDetectionResult(
                primary_language="English",
                language_code="en",
                confidence=0.7,
                warning="Limited alphabetic tokens found; assumed English."
            )

        token_set = set(tokens)
        scores: Dict[str, float] = {}

        for lang, stopwords in LATIN_STOPWORDS.items():
            overlap = token_set.intersection(stopwords)
            # Weighted by overlap count and frequency in sample
            freq_hits = sum(1 for t in tokens if t in stopwords)
            score = (len(overlap) * 2.0) + (freq_hits / len(tokens) * 10.0)
            scores[lang] = score

        best_lang, best_score = max(scores.items(), key=lambda x: x[1])

        # If zero or minimal stopword matches, check langdetect if installed
        if best_score < 1.0:
            try:
                import langdetect
                det_code = langdetect.detect(sample)
                if det_code in SUPPORTED_LANGUAGES:
                    return LanguageDetectionResult(
                        primary_language=SUPPORTED_LANGUAGES[det_code],
                        language_code=det_code,
                        confidence=0.80,
                        warning=None,
                        char_counts=script_counts
                    )
            except Exception:
                pass
            # Default to English with uncertainty note
            return LanguageDetectionResult(
                primary_language="English",
                language_code="en",
                confidence=0.55,
                warning="Low lexical certainty for Latin script; defaulted to English."
            )

        # Calculate relative confidence
        total_score = sum(scores.values()) or 1.0
        conf = round(min(0.99, max(0.65, best_score / total_score + 0.35)), 2)

        # Check for mixed languages in Latin text
        additional = []
        is_mixed = False
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_scores) > 1:
            second_lang, second_score = sorted_scores[1]
            if second_score >= 3.0 and (second_score / best_score) >= 0.40:
                additional.append(second_lang)
                is_mixed = True

        warning = None
        if conf < 0.60:
            warning = f"Language detection confidence is moderate ({conf:.0%})."

        return LanguageDetectionResult(
            primary_language=SUPPORTED_LANGUAGES.get(best_lang, best_lang.title()),
            language_code=best_lang,
            confidence=conf,
            additional_languages=additional,
            is_mixed=is_mixed,
            warning=warning,
            char_counts=script_counts
        )


language_detector = LanguageDetector()
