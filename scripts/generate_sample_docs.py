"""Generate realistic benchmark PDF sample documents using ReportLab."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def build_pdf(filename: str, story: list) -> Path:
    filepath = SAMPLE_DIR / filename
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    doc.build(story)
    return filepath


def generate_all_samples():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8
    )
    bold_body = ParagraphStyle(
        'DocBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    # 1. ApexCorp Annual Report FY2024
    story1 = []
    story1.append(Paragraph("ApexCorp Solutions Limited — Annual Report FY2024", title_style))
    story1.append(Paragraph("Document Type: Annual Financial Report | Reporting Period: April 2023 - March 2024", bold_body))
    story1.append(Spacer(1, 10))
    story1.append(Paragraph("Executive Overview", h2_style))
    story1.append(Paragraph(
        "ApexCorp Solutions Limited is a leading enterprise technology company delivering scalable cloud infrastructure, "
        "enterprise artificial intelligence workflows, and IT strategic consulting. In the fiscal year 2023-2024 (FY2024), "
        "ApexCorp demonstrated disciplined operational performance, achieving a total revenue of INR 100 Crore. "
        "The company expanded its core cloud platform while maintaining strict expense management.", body_style
    ))
    story1.append(Spacer(1, 8))
    story1.append(Paragraph("Financial Performance Summary (FY2024)", h2_style))
    
    fin_data_2024 = [
        ["Financial Metric", "FY2024 Value (INR)", "Margin / Ratio", "Key Highlights"],
        ["Total Revenue", "100.0 Cr", "100.0%", "Driven by robust enterprise cloud customer additions"],
        ["Operating Expenses", "70.0 Cr", "70.0%", "Infrastructure, personnel, and sales operations"],
        ["EBITDA", "35.0 Cr", "35.0%", "Strong core operational profitability"],
        ["Net Profit (PAT)", "30.0 Cr", "30.0%", "Net profit after taxes and depreciation"],
        ["Cash Flow from Operations", "22.0 Cr", "22.0%", "Consistent cash generation from client retainers"],
        ["Total Debt", "40.0 Cr", "0.40 Debt/Equity", "Long-term low-interest institutional loans"]
    ]
    t1 = Table(fin_data_2024, colWidths=[140, 110, 100, 180])
    t1.setStyle(table_style)
    story1.append(t1)

    story1.append(PageBreak())
    story1.append(Paragraph("Business Segment Breakdown (Page 2)", h2_style))
    seg_data_2024 = [
        ["Business Division", "Revenue (INR Cr)", "Share of Total", "Growth Trajectory"],
        ["Cloud Computing", "55.0 Cr", "55.0%", "High demand for multi-region hybrid hosting"],
        ["Enterprise AI", "30.0 Cr", "30.0%", "Pilot deployments of automated analytics"],
        ["Strategic Consulting", "15.0 Cr", "15.0%", "Stable recurring advisory contracts"]
    ]
    t2 = Table(seg_data_2024, colWidths=[140, 110, 100, 180])
    t2.setStyle(table_style)
    story1.append(t2)

    story1.append(Spacer(1, 10))
    story1.append(Paragraph("Risk Factors and Operational Challenges", h2_style))
    story1.append(Paragraph(
        "1. Competitive Pressure: Intense pricing competition from global hyperscale vendors.\n"
        "2. Foreign Currency Fluctuation: Exposure to USD/EUR volatility on software licensing contracts.\n"
        "3. Supply Chain Volatility: Hardware delivery lead times for specialized networking components.", body_style
    ))
    story1.append(Paragraph("Management Discussion and Outlook", h2_style))
    story1.append(Paragraph(
        "Management plans to accelerate investments into next-generation generative AI infrastructure in FY2025. "
        "While this capital expenditure may temporarily elevate short-term operating expenses, the leadership believes "
        "it will secure long-term technological leadership.", body_style
    ))
    build_pdf("ApexCorp_Annual_Report_FY2024.pdf", story1)

    # 2. ApexCorp Annual Report FY2025
    story2 = []
    story2.append(Paragraph("ApexCorp Solutions Limited — Annual Report FY2025", title_style))
    story2.append(Paragraph("Document Type: Annual Financial Report | Reporting Period: April 2024 - March 2025", bold_body))
    story2.append(Spacer(1, 10))
    story2.append(Paragraph("Executive Overview", h2_style))
    story2.append(Paragraph(
        "During fiscal year 2024-2025 (FY2025), ApexCorp Solutions expanded its top-line revenue to INR 112 Crore, "
        "representing a year-over-year revenue increase of 12.0%. However, operating expenses rose substantially to INR 86 Crore, "
        "a surge of 22.86%. Consequently, Net Profit declined from INR 30.0 Crore in FY2024 to INR 26.0 Crore in FY2025, "
        "reflecting a profit decrease of 13.33%.", body_style
    ))
    story2.append(Spacer(1, 8))
    story2.append(Paragraph("Financial Performance Summary (FY2025)", h2_style))
    
    fin_data_2025 = [
        ["Financial Metric", "FY2025 Value (INR)", "Margin / Ratio", "Key Highlights"],
        ["Total Revenue", "112.0 Cr", "100.0%", "12.0% YoY growth driven by Enterprise AI expansion"],
        ["Operating Expenses", "86.0 Cr", "76.78%", "High GPU datacenter procurement and energy expenses"],
        ["EBITDA", "31.0 Cr", "27.68%", "Compressed by server amortization and cloud leasing costs"],
        ["Net Profit (PAT)", "26.0 Cr", "23.21%", "13.33% decline due to upfront AI compute spending"],
        ["Cash Flow from Operations", "18.0 Cr", "16.07%", "Impacted by supplier advances for hardware clusters"],
        ["Total Debt", "45.0 Cr", "0.45 Debt/Equity", "Additional 5 Cr facility taken for facility expansion"]
    ]
    t3 = Table(fin_data_2025, colWidths=[140, 110, 100, 180])
    t3.setStyle(table_style)
    story2.append(t3)

    story2.append(PageBreak())
    story2.append(Paragraph("Business Segment Breakdown (Page 2)", h2_style))
    seg_data_2025 = [
        ["Business Division", "Revenue (INR Cr)", "Share of Total", "Growth Trajectory"],
        ["Cloud Computing", "62.0 Cr", "55.36%", "Healthy 12.7% growth from recurring workloads"],
        ["Enterprise AI", "38.0 Cr", "33.93%", "Fastest growing division with 26.67% growth YoY"],
        ["Strategic Consulting", "12.0 Cr", "10.71%", "Contracted by 20.0% as clients shifted to automation"]
    ]
    t4 = Table(seg_data_2025, colWidths=[140, 110, 100, 180])
    t4.setStyle(table_style)
    story2.append(t4)

    story2.append(Spacer(1, 10))
    story2.append(Paragraph("Key Reasons for Profit Decline and Risk Indicators", h2_style))
    story2.append(Paragraph(
        "Management notes three primary drivers for the decline in net profit:\n"
        "1. Escalating GPU Compute and Datacenter Leasing: Infrastructure costs rose by INR 11.5 Crore.\n"
        "2. Senior AI Research Talent Recruitment: Compensation packages for specialized machine learning teams increased payroll.\n"
        "3. Consulting Division Headwinds: Traditional consulting revenue slowed from 15 Cr to 12 Cr.\n\n"
        "Emerging Risk Indicators:\n"
        "- Cybersecurity and Data Privacy: Regulatory scrutiny on customer data handling inside LLM pipelines.\n"
        "- Infrastructure Depreciation: Faster obsolescence of hardware clusters.", body_style
    ))
    build_pdf("ApexCorp_Annual_Report_FY2025.pdf", story2)

    # 3. NeuralVision Research Paper
    story3 = []
    story3.append(Paragraph("NeuralVision: Dynamic Multi-Scale Visual Reasoning with Sparse Transformers", title_style))
    story3.append(Paragraph("Authors: Dr. Elena Vance, Marcus Thorne, Rajesh Kumar | Academic Research Paper", bold_body))
    story3.append(Spacer(1, 10))
    story3.append(Paragraph("Abstract", h2_style))
    story3.append(Paragraph(
        "We introduce NeuralVision, a novel sparse-attention visual reasoning transformer architecture that dynamically "
        "routes attention tokens based on visual saliency and token entropy. In contrast to standard dense Vision Transformers "
        "which incur quadratic O(N^2) computational complexity, NeuralVision achieves sub-quadratic O(N log N) scaling "
        "while outperforming dense baselines across standard image classification benchmarks. On ImageNet-1K, NeuralVision-Base "
        "attains an 84.6% Top-1 accuracy with 34% lower FLOPs than ViT-Base.", body_style
    ))
    story3.append(Spacer(1, 8))
    story3.append(Paragraph("Methodology and Architectural Formulation", h2_style))
    story3.append(Paragraph(
        "Given an input tensor X in R^{B x C x H x W}, we extract hierarchical patch tokens through a progressive convolutional "
        "stem. A dynamic gating module estimates routing coefficients via softmax-normalized gumbel top-k selection. "
        "The sparse attention kernel computes affinity matrices exclusively among the top 25% highest variance tokens.", body_style
    ))
    story3.append(Spacer(1, 8))
    story3.append(Paragraph("Empirical Results on ImageNet-1K Benchmark", h2_style))
    research_table = [
        ["Model Architecture", "Params (M)", "FLOPs (G)", "Top-1 Accuracy (%)", "Latency (ms)"],
        ["ResNet-50 Baseline", "25.6M", "4.1G", "76.1%", "12.4ms"],
        ["ViT-B / 16", "86.6M", "17.6G", "79.8%", "31.2ms"],
        ["Swin-B Transformer", "88.0M", "15.4G", "83.5%", "28.5ms"],
        ["NeuralVision-Tiny (Ours)", "28.4M", "4.8G", "81.4%", "14.1ms"],
        ["NeuralVision-Base (Ours)", "84.2M", "11.6G", "84.6%", "21.8ms"]
    ]
    t5 = Table(research_table, colWidths=[150, 80, 80, 110, 80])
    t5.setStyle(table_style)
    story3.append(t5)
    story3.append(PageBreak())
    story3.append(Paragraph("Ablation Study and Conclusion (Page 2)", h2_style))
    story3.append(Paragraph(
        "Ablations reveal that token routing without entropy guidance suffers a 1.8% accuracy drop. "
        "The proposed sparse attention mechanism reduces memory footprint by 42% on high-resolution 512x512 inputs. "
        "In future work, we plan to extend NeuralVision to video and multimodal reasoning.", body_style
    ))
    build_pdf("NeuralVision_Research_Paper.pdf", story3)

    # 4. CloudServices Master Agreement
    story4 = []
    story4.append(Paragraph("CloudSphere Inc. — Master Cloud Services Agreement", title_style))
    story4.append(Paragraph("Legal Contract | Agreement ID: MSA-2024-8841 | Effective Date: January 1, 2024", bold_body))
    story4.append(Spacer(1, 10))
    story4.append(Paragraph("1. Purpose and Scope of Services", h2_style))
    story4.append(Paragraph(
        "This Master Services Agreement ('Agreement') is entered into between CloudSphere Technologies Inc. ('Provider') "
        "and ApexCorp Solutions Limited ('Customer'). Provider agrees to deliver multi-tenant cloud infrastructure, "
        "managed Kubernetes clusters, and automated continuous backup services as detailed in Exhibit A.", body_style
    ))
    story4.append(Spacer(1, 8))
    story4.append(Paragraph("2. Service Level Agreement (SLA) and Uptime Guarantee", h2_style))
    story4.append(Paragraph(
        "Provider guarantees a Monthly Service Uptime of not less than 99.95%. In the event of downtime exceeding "
        "permitted maintenance windows, Customer is entitled to SLA service credits as stipulated below:", body_style
    ))
    sla_table = [
        ["Monthly Uptime Percentage", "Service Credit (% of Monthly Fee)", "Remedy Window"],
        ["99.50% - 99.94%", "10% Credit", "Applied to next billing cycle"],
        ["99.00% - 99.49%", "25% Credit", "Applied to next billing cycle"],
        ["Below 99.00%", "50% Credit", "Immediate refund or credit option"]
    ]
    t6 = Table(sla_table, colWidths=[170, 180, 160])
    t6.setStyle(table_style)
    story4.append(t6)
    story4.append(Spacer(1, 10))
    story4.append(Paragraph("3. Limitation of Liability and Indemnification", h2_style))
    story4.append(Paragraph(
        "Neither party shall be liable for indirect, incidental, or consequential damages. The aggregate liability "
        "of either party arising under this Agreement shall not exceed the total fees paid by Customer during the "
        "preceding twelve (12) months, or INR 50,00,000 (Fifty Lakhs), whichever is lower.", body_style
    ))
    story4.append(Paragraph("4. Confidentiality and Termination", h2_style))
    story4.append(Paragraph(
        "Each party shall safeguard confidential information for a period of five (5) years following termination. "
        "Either party may terminate this agreement without cause upon thirty (30) days prior written notice.", body_style
    ))
    build_pdf("CloudServices_Master_Agreement.pdf", story4)

    # 5. Enterprise Hardware Invoice
    story5 = []
    story5.append(Paragraph("COMMERCIAL TAX INVOICE", title_style))
    story5.append(Paragraph("HighTech Computing Systems Ltd. | Invoice #: INV-2025-9823 | Date: February 14, 2025", bold_body))
    story5.append(Spacer(1, 10))
    story5.append(Paragraph("Billed To: ApexCorp Solutions Limited | GSTIN: 27AABCA1234F1Z9", body_style))
    story5.append(Paragraph("Payment Terms: Net 30 Days | Due Date: March 16, 2025", body_style))
    story5.append(Spacer(1, 8))
    invoice_data = [
        ["Line Item Description", "HSN Code", "Qty", "Unit Rate (INR)", "Total Amount (INR)"],
        ["ApexNode GPU Server (8x H100 SXM5)", "8471", "2", "16,00,000", "32,00,000"],
        ["NVMe-oF High-Speed Storage Array 100TB", "8471", "1", "4,50,000", "4,50,000"],
        ["400Gbps InfiniBand Switch Fabrics", "8517", "2", "95,000", "1,90,000"],
        ["Subtotal Before Taxes", "-", "-", "-", "38,40,000"],
        ["Integrated GST (IGST @ 18.0%)", "-", "-", "-", "6,91,200"],
        ["Grand Total Payable", "-", "-", "-", "INR 45,31,200"]
    ]
    t7 = Table(invoice_data, colWidths=[200, 60, 40, 100, 110])
    t7.setStyle(table_style)
    story5.append(t7)
    story5.append(Spacer(1, 10))
    story5.append(Paragraph("Bank Details for NEFT/RTGS Remittance:", bold_body))
    story5.append(Paragraph("Beneficiary: HighTech Computing Systems Ltd | Bank: State Bank of India | IFSC: SBIN0004521 | A/C: 38920199482", body_style))
    build_pdf("Enterprise_Hardware_Invoice_INV9823.pdf", story5)
    print("All 5 sample PDFs generated successfully in data/sample_docs.")


if __name__ == "__main__":
    generate_all_samples()
