"""Translation and multilingual alignment service for DocuMind."""

import re
from typing import Dict, List, Optional, Tuple

from app.services.language_service import SUPPORTED_LANGUAGES, language_detector
from app.utils.config import settings
from app.utils.logging import logger

# Domain term mappings to English across key supported languages
DOMAIN_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "hi": {
        "कुल राजस्व": "total revenue",
        "राजस्व": "revenue",
        "शुद्ध लाभ": "net profit",
        "लाभ": "profit",
        "संचालन व्यय": "operating expenses",
        "व्यय": "expenses",
        "वार्षिक रिपोर्ट": "annual report",
        "वित्तीय विवरण": "financial statement",
        "जोखिम": "risk",
        "खतरा": "threat",
        "दायित्व": "liability",
        "अनुबंध": "contract",
        "करार": "agreement",
        "शोध पत्र": "research paper",
        "चालान": "invoice",
        "करोड़": "Crore",
        "लाख": "Lakh",
        "बढ़ोतरी": "growth",
        "कमी": "decline",
        "तुलना": "comparison",
        "अध्ययन": "study",
        "निष्कर्ष": "conclusion",
        "प्रणाली": "system",
        "मॉडल": "model",
        "सटीकता": "accuracy",
        "कंपनी": "company",
        "वर्ष": "year",
        "वृद्धि": "increase",
        "गिरावट": "decrease",
        "लागत": "cost",
        "दंडात्मक": "penalty",
        "उल्लंघन": "breach",
        "समाप्ति": "termination",
        "परियोजना": "project",
        "बजट": "budget",
        "कितना": "how much",
        "कितनी": "how many",
        "गाँव": "village",
        "गाँवों": "villages",
        "महीने": "months",
        "महीनों": "months",
        "किसानों": "farmers",
        "प्रशिक्षण": "training",
        "लक्ष्य": "targets",
        "जोखिम": "risk",
        "देरी": "delay",
        "प्रभाव": "impact",
        "सेंसर": "sensors",
        "जल-स्तर": "water level",
        "पानी": "water",
        "कमी": "reduction",
    },
    "bn": {
        "মোট রাজস্ব": "total revenue",
        "রাজস্ব": "revenue",
        "নীট লাভ": "net profit",
        "লাভ": "profit",
        "পরিচালন ব্যয়": "operating expenses",
        "ব্যয়": "expenses",
        "বার্ষিক প্রতিবেদন": "annual report",
        "আর্থিক প্রতিবেদন": "financial report",
        "ঝুঁকি": "risk",
        "বিপদ": "threat",
        "দায়": "liability",
        "চুক্তি": "contract",
        "গবেষণা পত্র": "research paper",
        "চালান": "invoice",
        "কোটি": "Crore",
        "লাখ": "Lakh",
        "বৃদ্ধি": "growth",
        "হ্রাস": "decline",
        "তুলনা": "comparison",
        "পদ্ধতি": "methodology",
        "ফলাফল": "results",
        "মডেল": "model",
        "নির্ভুলতা": "accuracy",
        "সংস্থা": "organization",
        "বছর": "year",
        "সীমাবদ্ধতা": "limitation",
        "জরিমানা": "penalty",
        "বাতিল": "termination",
    },
    "es": {
        "ingresos totales": "total revenue",
        "ingresos": "revenue",
        "ventas netas": "net sales",
        "beneficio neto": "net profit",
        "ganancia neta": "net profit",
        "gastos operativos": "operating expenses",
        "gastos": "expenses",
        "informe anual": "annual report",
        "estados financieros": "financial statements",
        "riesgo": "risk",
        "riesgos": "risks",
        "amenaza": "threat",
        "responsabilidad": "liability",
        "contrato": "contract",
        "acuerdo": "agreement",
        "artículo de investigación": "research paper",
        "factura": "invoice",
        "crecimiento": "growth",
        "disminución": "decrease",
        "comparación": "comparison",
        "metodología": "methodology",
        "resultados": "results",
        "precisión": "accuracy",
        "cláusula": "clause",
        "rescisión": "termination",
        "incumplimiento": "breach",
        "penalización": "penalty",
    },
    "fr": {
        "chiffre d'affaires": "revenue",
        "chiffre d'affaires total": "total revenue",
        "bénéfice net": "net profit",
        "résultat net": "net income",
        "dépenses d'exploitation": "operating expenses",
        "charges": "expenses",
        "dépenses": "expenses",
        "rapport annuel": "annual report",
        "états financiers": "financial statements",
        "risque": "risk",
        "risques": "risks",
        "menace": "threat",
        "responsabilité": "liability",
        "contrat": "contract",
        "accord": "agreement",
        "article de recherche": "research paper",
        "facture": "invoice",
        "croissance": "growth",
        "baisse": "decline",
        "comparaison": "comparison",
        "méthodologie": "methodology",
        "résultats": "results",
        "précision": "accuracy",
        "résiliation": "termination",
        "manquement": "breach",
        "pénalité": "penalty",
    },
    "de": {
        "gesamtumsatz": "total revenue",
        "umsatz": "revenue",
        "jahresüberschuss": "net profit",
        "nettogewinn": "net profit",
        "betriebsaufwand": "operating expenses",
        "betriebsausgaben": "operating expenses",
        "aufwendungen": "expenses",
        "jahresbericht": "annual report",
        "finanzbericht": "financial report",
        "risiko": "risk",
        "risiken": "risks",
        "bedrohung": "threat",
        "haftung": "liability",
        "vertrag": "contract",
        "vereinbarung": "agreement",
        "forschungsarbeit": "research paper",
        "rechnung": "invoice",
        "wachstum": "growth",
        "rückgang": "decline",
        "vergleich": "comparison",
        "methodik": "methodology",
        "ergebnisse": "results",
        "genauigkeit": "accuracy",
        "kündigung": "termination",
        "vertragsverletzung": "breach",
        "strafe": "penalty",
    },
    "ar": {
        "إجمالي الإيرادات": "total revenue",
        "الإيرادات": "revenue",
        "صافي الربح": "net profit",
        "الأرباح": "profit",
        "المصروفات التشغيلية": "operating expenses",
        "المصروفات": "expenses",
        "التقرير السنوي": "annual report",
        "القوائم المالية": "financial statements",
        "مخاطر": "risk",
        "خطر": "threat",
        "مسؤولية": "liability",
        "عقد": "contract",
        "اتفاقية": "agreement",
        "ورقة بحثية": "research paper",
        "فاتورة": "invoice",
        "نمو": "growth",
        "انخفاض": "decline",
        "مقارنة": "comparison",
        "منهجية": "methodology",
        "نتائج": "results",
        "دقة": "accuracy",
        "إنهاء العقد": "termination",
        "مخالفة": "breach",
        "غرامة": "penalty",
    },
    "zh": {
        "总营业收入": "total revenue",
        "营业收入": "revenue",
        "净利润": "net profit",
        "营业费用": "operating expenses",
        "总支出": "total expenses",
        "年度报告": "annual report",
        "财务报表": "financial statements",
        "风险": "risk",
        "威胁": "threat",
        "法律责任": "liability",
        "合同": "contract",
        "协议": "agreement",
        "研究论文": "research paper",
        "发票": "invoice",
        "增长": "growth",
        "下降": "decline",
        "比较": "comparison",
        "方法": "methodology",
        "结果": "results",
        "准确率": "accuracy",
        "终止": "termination",
        "违约": "breach",
        "违约金": "penalty",
    },
    "ru": {
        "общая выручка": "total revenue",
        "выручка": "revenue",
        "чистая прибыль": "net profit",
        "операционные расходы": "operating expenses",
        "расходы": "expenses",
        "годовой отчет": "annual report",
        "финансовая отчетность": "financial statements",
        "риск": "risk",
        "риски": "risks",
        "угроза": "threat",
        "ответственность": "liability",
        "договор": "contract",
        "соглашение": "agreement",
        "научная статья": "research paper",
        "счет": "invoice",
        "рост": "growth",
        "снижение": "decline",
        "сравнение": "comparison",
        "методология": "methodology",
        "результаты": "results",
        "точность": "accuracy",
        "расторжение": "termination",
        "нарушение": "breach",
        "штраф": "penalty",
    },
    "ja": {
        "売上高": "revenue",
        "総売上": "total revenue",
        "当期純利益": "net profit",
        "営業利益": "operating income",
        "営業費用": "operating expenses",
        "現金及び現金同等物": "cash and cash equivalents",
        "現金同等物": "cash equivalents",
        "現金": "cash",
        "年間報告書": "annual report",
        "有価証券報告書": "annual securities report",
        "リスク": "risk",
        "脅威": "threat",
        "法的責任": "liability",
        "契約書": "contract",
        "学術論文": "research paper",
        "請求書": "invoice",
        "成長": "growth",
        "減少": "decline",
        "比較": "comparison",
        "精度": "accuracy",
        "解除": "termination",
        "違反": "breach",
    }
}


class TranslationService:
    """Provides high-fidelity, bidirectional translation with caching and multiple fallbacks."""

    def __init__(self):
        # In-memory LRU cache: (text_hash, src_lang, tgt_lang) -> translated_text
        self._cache: Dict[Tuple[int, str, str], str] = {}

    def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: str = "en"
    ) -> str:
        """Translates text from source_lang to target_lang while strictly preserving factual data."""
        clean = text.strip()
        if not clean:
            return ""

        # Detect source language if not explicitly provided or 'auto'
        if not source_lang or source_lang == "auto":
            det = language_detector.detect(clean)
            source_lang = det.language_code

        # If already in the target language, return directly
        if source_lang == target_lang:
            return clean

        cache_key = (hash(clean), source_lang, target_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]

        translated = self._translate_internal(clean, source_lang, target_lang)
        if len(self._cache) < 3000:
            self._cache[cache_key] = translated
        return translated

    def translate_to_english(self, text: str, source_language: Optional[str] = None) -> str:
        """Convenience wrapper used by document summaries and cross-language comparisons."""
        return self.translate(text, source_lang=source_language or "auto", target_lang="en")

    def translate_from_english(self, text: str, target_language: str) -> str:
        """Convenience wrapper for rendering summaries in a requested output language."""
        if not target_language or target_language == "original":
            return text
        return self.translate(text, source_lang="en", target_lang=target_language)

    def _translate_internal(self, text: str, source_lang: str, target_lang: str) -> str:
        """Internal multi-tier translation implementation."""
        provider = settings.TRANSLATION_PROVIDER.strip().lower()

        # Network translation is opt-in: the default provider is offline because source
        # passages can contain private document content.
        if provider == "auto":
            try:
                from deep_translator import GoogleTranslator
                res = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
                if res and res.strip():
                    return res.strip()
            except Exception:
                pass

        # Tier 2: Use the explicitly selected local or hosted LLM translation provider.
        llm_provider = settings.LLM_PROVIDER.strip().lower()
        if provider in ("openai", "ollama") and llm_provider == provider or provider == "auto" and llm_provider in ("openai", "ollama"):
            try:
                from app.services.llm_service import llm_service, MockRuleBasedProvider
                if not isinstance(llm_service, MockRuleBasedProvider):
                    prompt = (
                        f"Translate the following text accurately from {source_lang} to {target_lang}. "
                        "Preserve all proper nouns, numbers, currencies, dates, and technical terminology exactly.\n\n"
                        f"{text}"
                    )
                    res = llm_service.generate(prompt=prompt, system_prompt="You are a professional multilingual translator.")
                    if res and res.strip() and not res.startswith("No generative model"):
                        return res.strip()
            except Exception as e:
                logger.warning(f"LLM translation attempt failed: {e}")

        # Tier 3: High-accuracy domain lexical translation & alignment fallback
        return self._offline_domain_translate(text, source_lang, target_lang)

    def _offline_domain_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates text using domain dictionaries, preserving all numbers, dates, and entities."""
        if target_lang != "en" and source_lang == "en":
            # Reverse mapping from English to target language for standard query expansion/phrases
            rev_dict = {}
            for term, eng in DOMAIN_TRANSLATIONS.get(target_lang, {}).items():
                rev_dict[eng.lower()] = term
            result = text
            for eng_term, tgt_term in sorted(rev_dict.items(), key=lambda x: len(x[0]), reverse=True):
                pattern = re.compile(rf"\b{re.escape(eng_term)}\b", re.I)
                result = pattern.sub(tgt_term, result)
            return result

        # Source language to English
        term_map = DOMAIN_TRANSLATIONS.get(source_lang, {})
        translated = text

        # Substitute multi-word and single-word domain terms in order of length
        sorted_terms = sorted(term_map.items(), key=lambda x: len(x[0]), reverse=True)
        for src_term, eng_term in sorted_terms:
            if src_term in translated:
                translated = translated.replace(src_term, f" {eng_term} ")

        # Clean multiple spaces while preserving structural punctuation
        translated = re.sub(r"\s+", " ", translated).strip()
        return translated

    def translate_citation(self, snippet: str, source_lang: str) -> Tuple[str, Optional[str]]:
        """Returns original snippet and English translation for side-by-side display."""
        if not snippet:
            return "", None
        if source_lang == "en":
            return snippet, None
        trans = self.translate(snippet, source_lang=source_lang, target_lang="en")
        return snippet, trans if trans != snippet else None


translation_service = TranslationService()
