"""Document Classification Agent for categorizing document type and domain with confidence scoring."""

from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.models.state import AgentState
from app.utils.logging import logger


class ClassifierAgent(BaseAgent):
    """Classifies uploaded documents into types and domains with confidence scoring."""

    def __init__(self):
        super().__init__(
            name="Classifier Agent",
            description="Analyzes document structure, vocabulary, and patterns to determine document type and domain."
        )

    def classify_document(self, text: str, filename: str) -> Dict[str, Any]:
        """Classifies document content across languages using heuristic pattern matching."""
        text_sample = text[:4000].lower()
        fn_lower = filename.lower()

        from app.services.language_service import language_detector
        lang_res = language_detector.detect(text_sample or filename)

        # Heuristic scoring
        scores = {
            "Annual Report": 0.0,
            "Commercial Invoice": 0.0,
            "Master Services Agreement": 0.0,
            "Research Paper": 0.0,
            "General Business Report": 0.1
        }

        # Filename indicators across languages
        if any(w in fn_lower for w in ["annual", "financial", "report", "fy20", "वार्षिक", "বার্ষিক", "anual", "annuel", "jahresbericht", "年度"]):
            scores["Annual Report"] += 0.4
        if any(w in fn_lower for w in ["invoice", "bill", "inv-", "tax", "चालान", "চালান", "factura", "facture", "rechnung", "发票"]):
            scores["Commercial Invoice"] += 0.4
        if any(w in fn_lower for w in ["agreement", "contract", "msa", "sla", "terms", "अनुबंध", "करार", "চুক্তি", "contrato", "contrat", "vertrag", "合同"]):
            scores["Master Services Agreement"] += 0.4
        if any(w in fn_lower for w in ["paper", "research", "transformer", "neural", "arxiv", "शोध", "গবেষণা", "articulo", "thèse", "论文"]):
            scores["Research Paper"] += 0.4

        # Annual / Financial Report text heuristics across languages
        financial_terms = [
            # English
            "balance sheet", "ebitda", "net profit", "pat", "fiscal year", "revenue", "cash flow", "operating expenses",
            # Hindi
            "तुलन पत्र", "कुल राजस्व", "राजस्व", "शुद्ध लाभ", "वित्तीय विवरण", "रोकड़ प्रवाह", "संचालन व्यय",
            # Bengali
            "মোট রাজস্ব", "রাজস্ব", "নীট লাভ", "আর্থিক প্রতিবেদন", "পরিচালন ব্যয়",
            # Spanish
            "balance general", "ingresos totales", "ingresos", "beneficio neto", "flujo de caja", "gastos operativos",
            # French
            "chiffre d'affaires", "bénéfice net", "résultat net", "bilan", "dépenses d'exploitation",
            # German
            "gesamtumsatz", "umsatz", "jahresüberschuss", "bilanz", "betriebsaufwand",
            # Arabic
            "الميزانية العمومية", "إجمالي الإيرادات", "صافي الربح", "القوائم المالية",
            # Chinese
            "资产负债表", "营业收入", "净利润", "现金流量", "年度报告"
        ]
        if any(w in text_sample for w in financial_terms):
            scores["Annual Report"] += 0.55

        # Invoice heuristics across languages
        invoice_terms = [
            # English
            "invoice #", "gstin", "hsn code", "grand total", "payment terms", "due date", "bill to",
            # Hindi
            "चालान", "बीजक", "कर संख्या", "कुल योग", "देय तिथि",
            # Bengali
            "চালান", "বিল নং", "মোট প্রদেয়",
            # Spanish
            "factura", "nif", "cif", "total a pagar", "fecha de vencimiento",
            # French
            "facture", "tva", "total ttc", "date d'échéance",
            # German
            "rechnung", "rechnungsnummer", "steuer-nr", "gesamtbetrag", "fälligkeitsdatum",
            # Arabic
            "فاتورة", "الرقم الضريبي", "المجموع الإجمالي", "تاريخ الاستحقاق",
            # Chinese
            "发票号码", "纳税人识别号", "总计金额", "付款期限"
        ]
        if any(w in text_sample for w in invoice_terms):
            scores["Commercial Invoice"] += 0.55

        # Legal / Contract heuristics across languages
        legal_terms = [
            # English
            "master services agreement", "limitation of liability", "indemnification", "uptime guarantee", "confidentiality", "governing law", "termination clause",
            # Hindi
            "अनुबंध", "करार", "दायित्व की सीमा", "क्षतिपूर्ति", "गोपनीयता",
            # Bengali
            "চুক্তিপত্র", "দায়বদ্ধতার সীমাবদ্ধতা", "ক্ষতিপূরণ", "গোপনীয়তা",
            # Spanish
            "contrato de servicios", "limitación de responsabilidad", "indemnización", "confidencialidad", "rescisión",
            # French
            "contrat de prestation", "limitation de responsabilité", "indemnisation", "confidentialité", "résiliation",
            # German
            "dienstleistungsvertrag", "haftungsbeschränkung", "freistellung", "vertraulichkeit", "kündigung",
            # Arabic
            "اتفاقية خدمات", "تحديد المسؤولية", "التعويض", "سرية المعلومات", "إنهاء العقد",
            # Chinese
            "服务协议", "责任限制", "赔偿条款", "保密义务", "违约责任", "合同终止"
        ]
        if any(w in text_sample for w in legal_terms):
            scores["Master Services Agreement"] += 0.55

        # Research Paper heuristics across languages
        research_terms = [
            # English
            "abstract", "methodology", "ablation study", "top-1 accuracy", "benchmark", "flops", "dataset", "experimental results",
            # Hindi
            "शोध पत्र", "सार", "कार्यप्रणाली", "प्रयोगात्मक परिणाम",
            # Bengali
            "গবেষণা", "সারসংক্ষেপ", "পদ্ধতি", "পরীক্ষামূলক ফলাফল",
            # Spanish
            "resumen", "metodología", "estudio de ablación", "resultados experimentales", "conjunto de datos",
            # French
            "résumé", "méthodologie", "résultats expérimentaux", "jeu de données",
            # German
            "zusammenfassung", "methodik", "experimentelle ergebnisse", "datensatz",
            # Arabic
            "ملخص البحث", "المنهجية", "النتائج التجريبية", "مجموعة البيانات",
            # Chinese
            "摘要", "研究方法", "实验结果", "数据集", "消融实验"
        ]
        if any(w in text_sample for w in research_terms):
            scores["Research Paper"] += 0.55

        # Select highest scoring
        best_type, best_score = max(scores.items(), key=lambda x: x[1])
        confidence = min(0.98, round(best_score, 2))

        domain_mapping = {
            "Annual Report": "Finance",
            "Commercial Invoice": "Billing / Procurement",
            "Master Services Agreement": "Legal / Compliance",
            "Research Paper": "Academic / AI",
            "General Business Report": "General Business"
        }

        return {
            "document_type": best_type,
            "domain": domain_mapping.get(best_type, "General"),
            "confidence": confidence,
            "detected_language": lang_res.primary_language,
            "language_code": lang_res.language_code,
            "reasoning": f"Multilingual heuristic keyword score for {best_type} ({lang_res.primary_language}): {confidence:.0%}. This is a rule score, not a calibrated model probability."
        }

    def run(self, state: AgentState) -> AgentState:
        """Updates AgentState with classified document types."""
        state.current_agent = self.name
        for doc_id, filename in state.active_documents.items():
            if doc_id not in state.document_types:
                res = self.classify_document("", filename)
                state.document_types[doc_id] = res["document_type"]
                state.add_log(
                    agent_name=self.name,
                    action="Document Classification",
                    detail=f"Classified '{filename}' as {res['document_type']} (Domain: {res['domain']}, Confidence: {res['confidence']})"
                )
        return state


classifier_agent = ClassifierAgent()
