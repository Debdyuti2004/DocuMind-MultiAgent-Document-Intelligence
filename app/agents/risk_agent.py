"""Extractive risk indicator detection grounded in retrieved evidence."""

import re
from app.agents.base_agent import BaseAgent
from app.models.state import AgentState


RISK_PATTERN = re.compile(
    r"\b(risk|threat|challenge|vulnerabilit\w*|liabilit\w*|penalt\w*|exposure|uncertain\w*|"
    r"may result|subject to|termination|breach|non-compliance|noncompliance|"
    r"जोखिम|खतरा|दायित्व|चुनौती|अनिश्चित|दंड|उल्लंघन|समाप्ति|"
    r"ঝুঁকি|বিপদ|দায়|চ্যালেঞ্জ|জরিমানা|লঙ্ঘন|বাতিল|"
    r"riesgo\w*|amenaza\w*|vulnerabilidad\w*|responsabilidad\w*|sanción|multa|penalización|incumplimiento|rescisión|"
    r"risque\w*|menace\w*|vulnérabilité\w*|responsabilité\w*|pénalité\w*|manquement|résiliation|"
    r"risiko|risiken|bedrohung|gefahr|haftung|vertragsverletzung|kündigung|"
    r"مخاطر|خطر|تهديد|مسؤولية|غرامة|مخالفة|إنهاء|"
    r"风险|威胁|漏洞|法律责任|处罚|违约|终止|"
    r"リスク|脅威|法的責任|ペナルティ|契約解除|違反)\b",
    re.I,
)


class RiskDetectionAgent(BaseAgent):
    """Surfaces source sentences that contain explicit risk-related wording across languages."""

    def __init__(self):
        super().__init__(name="Risk Detection Agent", description="Finds explicit risk-related statements in retrieved source text.")

    def run(self, state: AgentState) -> AgentState:
        state.current_agent = self.name
        from app.services.translation_service import translation_service

        indicators = []
        seen = set()
        for chunk in state.retrieved_chunks:
            text_to_scan = chunk.text
            for part in re.split(r"(?<=[.!?])\s+|\n+", text_to_scan):
                sentence = re.sub(r"\s+", " ", part).strip(" •\t")
                if not sentence or not RISK_PATTERN.search(sentence) or sentence.lower() in seen:
                    continue
                seen.add(sentence.lower())
                match = RISK_PATTERN.search(sentence)
                severity = "Unrated"
                surrounding = sentence[max(0, match.start() - 25):match.end() + 25].lower()
                if re.search(r"\b(high|critical|severe|उच्च|गंभीर|alto|crítico|grave|hoch|kritisch|عالي|حرجة|高|重大)\b", surrounding):
                    severity = "High"
                elif re.search(r"\b(medium|moderate|मध्यम|medio|moderado|moyen|modéré|mittel|متوسط|中等)\b", surrounding):
                    severity = "Medium"
                elif re.search(r"\b(low|निम्न|कम|bajo|faible|gering|منخفض|低|軽微)\b", surrounding):
                    severity = "Low"
                indicators.append({
                    "category": "Source disclosure",
                    "label": "Explicit risk-related text",
                    "finding": sentence,
                    "evidence": sentence,
                    "severity": severity,
                    "document_name": chunk.filename,
                    "document_id": chunk.document_id,
                    "page": chunk.page,
                })

        state.risk_indicators = indicators
        state.add_log(
            agent_name=self.name,
            action="Risk Text Extraction",
            detail=f"Found {len(indicators)} risk-related source sentence(s); severity is shown only when stated in evidence.",
            status="completed" if indicators else "warning",
        )
        return state


risk_agent = RiskDetectionAgent()
