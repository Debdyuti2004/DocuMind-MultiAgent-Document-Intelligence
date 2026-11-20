"""Extractive document summaries and evidence-backed comparisons with multilingual intelligence."""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.document.metadata import registry
from app.models.schemas import (
    ComparisonMetric,
    CompareResponse,
    DocumentSummary,
    SourceCitation,
)
from app.rag.vector_store import vector_store
from app.services.language_service import language_detector
from app.services.translation_service import translation_service


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?।\u0964\u0965。؟])\s+|\n+", text)
    return [re.sub(r"\s+", " ", part).strip(" •\t") for part in parts if len(part.strip()) > 30]


def summarize_document(doc_id: str, filename: str, doc_type: str, pages: list, tables: list) -> DocumentSummary:
    """Builds an extractive summary from parsed text with multilingual detection and English output by default."""
    full_text = "\n".join(getattr(page, "text", "") or "" for page in pages)
    detection = language_detector.detect(full_text)
    sentences = _sentences(full_text)
    key_facts = list(dict.fromkeys(sentences))[:6]
    orig_executive_summary = " ".join(key_facts[:3]) if key_facts else "No readable text was extracted from this document."

    # If document is non-English, produce English executive summary by default
    is_non_english = detection.language_code != "en" and detection.confidence > 0.4
    if is_non_english and key_facts:
        executive_summary = translation_service.translate_to_english(
            orig_executive_summary, source_language=detection.language_code
        )
    else:
        executive_summary = orig_executive_summary

    organizations = list(dict.fromkeys(re.findall(
        r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}\s+(?:Inc\.?|LLC|Ltd\.?|Limited|Corporation|Corp\.?|University|Institute|GmbH|SA|SL|SRL|Pvt|Private|Limited)\b",
        full_text,
    )))[:8]

    # Multilingual amounts including global currencies and regional denominators
    amounts = list(dict.fromkeys(re.findall(
        r"(?:INR|USD|EUR|GBP|JPY|CNY|RUB|₹|\$|€|£|¥|元|₽|₩)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:Cr|Crore|Lakh|करोड़|लाख|कोटी|M|B|K|million|billion|millones|milliards|миллион))?",
        full_text,
        flags=re.IGNORECASE,
    )))[:10]

    dates = list(dict.fromkeys(re.findall(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre|Janvier|Février|Mars|Avril|Mai|Juin|Juillet|Août|Septembre|Octobre|Novembre|Décembre|Januar|Februar|März|Mai|Juni|Juli|Oktober|Dezember|जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर)\s+\d{1,2},?\s+\d{4}|\bFY\s?\d{4}\b|\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b|\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b",
        full_text,
        flags=re.IGNORECASE,
    )))[:8]

    topics = list(dict.fromkeys(
        section.get("heading", "").strip()
        for page in pages for section in getattr(page, "sections", [])
        if section.get("heading", "").strip() and section.get("heading", "").strip().lower() != "general"
    ))[:10]

    risk_terms = re.compile(
        r"(?i)\b(risk|threat|liabilit\w*|penalt\w*|vulnerabilit\w*|exposure|uncertain\w*|may result|subject to|riesgo|peligro|menace|gefahr|risiko|pericolo|risco|risico|risque|जोखिम|खतरा|दायित्व|ঝুঁকি|风险|위험|угроз\w*|риск\w*)\b"
    )
    risks = list(dict.fromkeys(sentence for sentence in sentences if risk_terms.search(sentence)))[:8]

    questions = [
        "What are the main points in this document?",
        "Which figures, dates, or named entities does it contain?",
        "What risks or limitations are explicitly mentioned?",
    ] if full_text.strip() else []

    return DocumentSummary(
        document_id=doc_id,
        filename=filename,
        document_type=doc_type,
        executive_summary=executive_summary,
        key_facts=key_facts,
        key_entities={"Organizations": organizations, "Amounts": amounts, "Dates / Periods": dates},
        key_topics=topics,
        important_findings=key_facts[3:6],
        potential_risks=risks,
        suggested_questions=questions,
        language=detection.language_name,
        language_code=detection.language_code,
        is_translated=is_non_english and executive_summary != orig_executive_summary,
        original_language_summary=orig_executive_summary if is_non_english else None,
    )


METRIC_LABELS = {
    "Revenue": (
        "total revenue", "revenue", "turnover", "net sales",
        "ingresos totales", "ingresos", "volumen de negocios", "ventas netas",
        "chiffre d'affaires", "recettes", "produits",
        "gesamtertrag", "umsatzerlöse", "umsatz", "ertrag",
        "ricavi totali", "ricavi", "fatturato",
        "receita total", "receita", "faturamento",
        "omzet", "totale inkomsten",
        "общая выручка", "выручка", "доход",
        "कुल राजस्व", "राजस्व", "कुल आय", "आय",
        "মোট রাজস্ব", "রাজস্ব", "মোট আয়",
        "总收入", "营业收入", "收入",
        "売上高", "総収益", "収益",
        "총수익", "매출액", "수익",
        "pendapatan", "gelir", "آمدنی"
    ),
    "Operating expenses": (
        "operating expenses", "total expenses", "expenses", "opex",
        "gastos operativos", "gastos de operacion", "gastos totales", "gastos",
        "dépenses d'exploitation", "charges d'exploitation", "dépenses totales",
        "betriebsaufwand", "betriebskosten", "gesamtaufwendungen",
        "spese operative", "costi operativi",
        "despesas operacionais", "despesas totais",
        "bedrijfskosten",
        "операционные расходы", "общие расходы",
        "परिचालन व्यय", "कुल व्यय", "खर्च",
        "পরিচালন ব্যয়", "মোট ব্যয়",
        "营业支出", "营运费用", "总支出",
        "営業費用", "経費",
        "운영 비용", "영업 비용", "총비용"
    ),
    "Net profit": (
        "net profit", "profit after tax", "pat", "net income",
        "beneficio neto", "ganancia neta", "utilidad neta",
        "bénéfice net", "résultat net",
        "nettogewinn", "jahresüberschuss", "reingewinn",
        "utile netto", "lucro líquido", "nettowinst",
        "чистая прибыль",
        "शुद्ध लाभ", "कुल लाभ", "मुनाफा",
        "নিট লাভ", "মোট लाभ",
        "净利润", "税后利润", "纯利",
        "当期純利益", "純利益",
        "순이익", "당기순이익",
        "laba bersih", "net kar", "خالص منافع"
    ),
    "EBITDA": (
        "ebitda", "ebit", "baida", "ebitda-marge"
    ),
    "Total debt": (
        "total debt", "debt", "deuda total", "deuda", "dette totale", "dette",
        "gesamtschulden", "schulden", "debito totale", "dívida total",
        "общий долг", "долг", "कुल ऋण", "ऋण", "कर्ज", "মোট ঋণ", "总负债", "부채"
    ),
    "Total assets": (
        "total assets", "assets", "activos totales", "activos", "total des actifs", "actifs",
        "gesamtvermögen", "aktiva", "attività totali", "ativos totais",
        "общие активы", "активы", "कुल संपत्ति", "संपत्ति", "মোট সম্পদ", "总资产", "자산"
    ),
    "Total liabilities": (
        "total liabilities", "liabilities", "pasivos totales", "pasivos", "total du passif", "passif",
        "gesamtverbindlichkeiten", "passiva", "passività totali", "passivos totais",
        "общие обязательства", "обязательства", "कुल देनदारियां", "देनदारियां", "মোট দায়", "负债"
    ),
    "Employees": (
        "employees", "headcount", "staff count", "empleados", "plantilla",
        "employés", "effectif", "mitarbeiter", "beschäftigte",
        "dipendenti", "funcionários", "medewerkers",
        "сотрудники", "персонал", "कर्मचारी", "কর্মী", "员工人数", "従業員数", "직원 수"
    ),
}


def _match_alias(alias: str, sentence: str) -> Optional[int]:
    """Finds alias start position in sentence across Latin and non-Latin scripts."""
    alias_lower = alias.lower()
    sent_lower = sentence.lower()
    if any(ord(c) > 127 for c in alias):
        idx = sent_lower.find(alias_lower)
        return idx if idx != -1 else None
    else:
        m = re.search(rf"\b{re.escape(alias)}\b", sent_lower)
        return m.start() if m else None


def _metric_evidence(chunks: Iterable[Dict[str, Any]]) -> Dict[str, Tuple[float, str, Dict[str, Any]]]:
    found: Dict[str, Tuple[float, str, Dict[str, Any]]] = {}
    amount_pattern = re.compile(
        r"(?<![A-Za-z\d])(?:₹|\$|€|£|¥|元|₽|₩|INR\s*|USD\s*|EUR\s*)?\s*(-?\d[\d,]*(?:\.\d+)?)\s*(%|Cr\b|Crore\b|Lakh\b|करोड़|लाख|कोटी|million\b|billion\b|millones\b|milliards\b)?",
        re.I,
    )
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in chunks:
        grouped.setdefault(str(chunk.get("document_id", "")), []).append(chunk)

    for document_chunks in grouped.values():
        for chunk in document_chunks:
            text = str(chunk.get("text", ""))
            sentences = [part.strip() for part in re.split(r"(?<=[.!?।\u0964\u0965。؟])\s+|\n+", text) if part.strip()]
            for label, aliases in METRIC_LABELS.items():
                if label in found:
                    continue
                for sentence in sentences:
                    match_pos = None
                    matched_len = 0
                    for alias in aliases:
                        pos = _match_alias(alias, sentence)
                        if pos is not None:
                            match_pos = pos
                            matched_len = len(alias)
                            break
                    if match_pos is None:
                        continue

                    # First check window following the label
                    window = sentence[match_pos + matched_len:]
                    window = re.sub(r"\b(?:FY\s?)?(?:19|20)\d{2}\b", " ", window, flags=re.I)
                    numbers = [item.group(1) for item in amount_pattern.finditer(window) if item.group(2) != "%"]

                    # If not found after label, check preceding window (e.g. for SOV structures like Hindi/Bengali: "50 करोड़ राजस्व")
                    if not numbers:
                        pre_window = sentence[:match_pos]
                        pre_window = re.sub(r"\b(?:FY\s?)?(?:19|20)\d{2}\b", " ", pre_window, flags=re.I)
                        pre_matches = [item.group(1) for item in amount_pattern.finditer(pre_window) if item.group(2) != "%"]
                        if pre_matches:
                            numbers = [pre_matches[-1]]

                    if not numbers:
                        continue
                    try:
                        use_second = len(numbers) > 1 and re.search(r"\b(?:from|се|de)\b.+\b(?:to|तक|a)\b", window, re.I | re.S)
                        value = float(numbers[1 if use_second else 0].replace(",", ""))
                    except ValueError:
                        continue
                    found[label] = (value, sentence[:1000], chunk)
                    break
    return found


def compare_documents(doc1_id: str, doc2_id: str, output_language: str = "en") -> CompareResponse:
    """Compares matched values extracted from each document's indexed text with multilingual support."""
    first = registry.get(doc1_id)
    second = registry.get(doc2_id)
    if not first or not second:
        raise ValueError("One or both document IDs were not found.")
    chunks1 = vector_store.get_document_chunks(doc1_id)
    chunks2 = vector_store.get_document_chunks(doc2_id)
    if not chunks1 or not chunks2:
        missing_names = [
            name for name, chunks in ((first.filename, chunks1), (second.filename, chunks2))
            if not chunks
        ]
        raise ValueError(
            "Source text is not indexed for: " + ", ".join(missing_names)
            + ". Upload the document again before comparing it."
        )
    values1, values2 = _metric_evidence(chunks1), _metric_evidence(chunks2)
    metrics: List[ComparisonMetric] = []
    citations: List[SourceCitation] = []
    differences: List[str] = []

    doc1_lang = getattr(first, "language_code", "en") or "en"
    doc2_lang = getattr(second, "language_code", "en") or "en"

    for label in METRIC_LABELS:
        item1, item2 = values1.get(label), values2.get(label)
        if not item1 or not item2:
            continue
        val1, evidence1, chunk1 = item1
        val2, evidence2, chunk2 = item2
        delta = round(val2 - val1, 4)
        pct = round(delta / abs(val1) * 100, 2) if val1 else None
        metrics.append(ComparisonMetric(
            metric=label,
            doc1_name=first.filename,
            doc1_value=val1,
            doc1_text=evidence1,
            doc2_name=second.filename,
            doc2_value=val2,
            doc2_text=evidence2,
            change_absolute=delta,
            change_percent=pct,
            interpretation="Calculated from the extracted values shown above." if val1 != val2 else "The extracted values match.",
        ))
        differences.append(f"{label}: {first.filename} — {evidence1}; {second.filename} — {evidence2}.")
        for filename, did, chunk, evidence, lang in (
            (first.filename, doc1_id, chunk1, evidence1, doc1_lang),
            (second.filename, doc2_id, chunk2, evidence2, doc2_lang),
        ):
            translated_snippet = (
                translation_service.translate_to_english(evidence, source_language=lang)
                if lang != "en" else evidence
            )
            citations.append(SourceCitation(
                document_name=filename,
                document_id=did,
                page=int(chunk.get("page", 1)),
                section=str(chunk.get("section", "Content")),
                snippet=evidence,
                original_snippet=evidence,
                translated_snippet=translated_snippet,
                language=lang,
            ))

    if metrics:
        summary = f"Compared {len(metrics)} metric(s) present in both indexed documents. Numeric changes are calculated from the extracted source lines."
    else:
        summary = "No shared numeric metrics were found. Source excerpts from both documents are shown for manual comparison."
        for metadata, chunks in ((first, chunks1), (second, chunks2)):
            chunk = max(chunks, key=lambda item: len(str(item.get("text", ""))))
            evidence = re.sub(r"\s+", " ", str(chunk.get("text", ""))).strip()[:700]
            if not evidence:
                continue
            differences.append(f"{metadata.filename}: {evidence}")
            lang = getattr(metadata, "language_code", "en") or "en"
            translated = (
                translation_service.translate_to_english(evidence, source_language=lang)
                if lang != "en" else evidence
            )
            citations.append(SourceCitation(
                document_name=metadata.filename,
                document_id=metadata.document_id,
                page=int(chunk.get("page", 1)),
                section=str(chunk.get("section", "Content")),
                snippet=evidence,
                original_snippet=evidence,
                translated_snippet=translated,
                language=lang,
            ))

    # Handle output language formatting if requested.
    effective_out_lang = output_language if output_language and output_language != "original" else "en"
    original_summary = summary
    original_differences = list(differences)
    if effective_out_lang != "en":
        summary = translation_service.translate_from_english(summary, target_language=effective_out_lang)
        differences = [
            translation_service.translate_from_english(d, target_language=effective_out_lang)
            for d in differences
        ]

    translation_applied = (
        summary != original_summary
        or differences != original_differences
        or any(c.translated_snippet and c.translated_snippet != c.original_snippet for c in citations)
    )

    return CompareResponse(
        doc1_id=doc1_id,
        doc1_name=first.filename,
        doc2_id=doc2_id,
        doc2_name=second.filename,
        comparison_summary=summary,
        metrics=metrics,
        key_differences=differences,
        citations=citations,
        agent_logs=[],
        output_language=effective_out_lang,
        doc1_language=doc1_lang,
        doc2_language=doc2_lang,
        translation_applied=translation_applied,
    )
