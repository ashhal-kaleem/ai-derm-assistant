import base64
import io
import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from PIL import Image

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class ReportService:
    """Generates doctor-ready vector PDF clinical reports using ReportLab."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        self.title_style = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0D47A1"),
            spaceAfter=4,
        )
        self.subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#546E7A"),
        )
        self.heading_style = ParagraphStyle(
            "SectionHeading",
            parent=self.styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1A237E"),
            spaceBefore=8,
            spaceAfter=4,
        )
        self.body_style = ParagraphStyle(
            "Body",
            parent=self.styles["BodyText"],
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#263238"),
        )
        self.disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#78909C"),
            alignment=1,  # Center
        )

    def _prepare_image_flowable(self, image_data: Any, max_size: int = 180) -> Optional[RLImage]:
        """Convert base64 string, PIL image, or bytes into an aspect-ratio preserved ReportLab Image."""
        if not image_data:
            return None
        try:
            buf = io.BytesIO()
            if isinstance(image_data, str):
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_data)
                pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
            elif isinstance(image_data, bytes):
                pil_img = Image.open(io.BytesIO(image_data)).convert("RGB")
            elif isinstance(image_data, Image.Image):
                pil_img = image_data.convert("RGB")
            else:
                return None

            pil_img.thumbnail((max_size, max_size))
            pil_img.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            return RLImage(buf, width=2.2 * inch, height=2.2 * inch)
        except Exception:
            return None

    def generate_pdf(
        self,
        prediction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        original_image_b64: Optional[str] = None,
        heatmap_b64: Optional[str] = None,
    ) -> bytes:
        """Render clinical diagnostic report into in-memory PDF buffer."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        story = []

        # 1. Header Banner
        date_str = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
        story.append(Paragraph("DermAssist AI — Clinical Analysis Report", self.title_style))
        story.append(Paragraph(f"Generated: {date_str} | Target: Educational Triage Consultation", self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D47A1"), spaceAfter=10, spaceBefore=4))

        # 2. Key Findings Summary Table
        class_name = prediction.get("class_name") or prediction.get("top_name") or "Skin Lesion"
        class_code = (prediction.get("predicted_class") or prediction.get("top_class") or "unk").upper()
        conf = float(prediction.get("confidence") or prediction.get("calibrated_confidence") or 0.0)
        risk_level = str(prediction.get("risk_level") or "green").lower()
        risk_label = prediction.get("risk_label") or ("See doctor urgently" if risk_level == "red" else ("Monitor" if risk_level == "yellow" else "Benign"))

        badge_color = "#D32F2F" if risk_level == "red" else ("#FBC02D" if risk_level == "yellow" else "#388E3C")

        summary_data = [
            [
                Paragraph("<b>Predicted Lesion:</b>", self.body_style),
                Paragraph(f"<b>{class_name}</b> ({class_code})", self.body_style),
                Paragraph("<b>Risk Triage:</b>", self.body_style),
                Paragraph(f"<font color='{badge_color}'><b>● {risk_label.upper()}</b></font>", self.body_style),
            ],
            [
                Paragraph("<b>Calibrated Confidence:</b>", self.body_style),
                Paragraph(f"<b>{conf * 100:.1f}%</b> (Temperature-Scaled)", self.body_style),
                Paragraph("<b>Uncertainty Level:</b>", self.body_style),
                Paragraph(f"<b>{str(prediction.get('uncertainty', 'Low')).capitalize()}</b>", self.body_style),
            ]
        ]
        summary_table = Table(summary_data, colWidths=[1.8 * inch, 2.0 * inch, 1.4 * inch, 2.0 * inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CFD8DC")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ECEFF1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))

        # 3. Visual Evidence (Photo + Grad-CAM Heatmap Side-by-Side)
        orig_img_flow = self._prepare_image_flowable(original_image_b64 or prediction.get("image_b64"))
        heat_img_flow = self._prepare_image_flowable(heatmap_b64 or prediction.get("heatmap_b64") or prediction.get("saliency_heatmap_base64"))

        if orig_img_flow or heat_img_flow:
            story.append(Paragraph("Visual Evidence & Explainability (Grad-CAM Attention)", self.heading_style))
            img_row = []
            img_labels = []
            if orig_img_flow:
                img_row.append(orig_img_flow)
                img_labels.append(Paragraph("<b>Input Photograph</b>", self.body_style))
            if heat_img_flow:
                img_row.append(heat_img_flow)
                img_labels.append(Paragraph("<b>Attention Heatmap (High Saliency in Red)</b>", self.body_style))

            if img_row:
                img_table = Table([img_row, img_labels], colWidths=[3.5 * inch] * len(img_row))
                img_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(img_table)
                story.append(Spacer(1, 8))

        # 4. Clinical Advisory Narrative (Groq LPU)
        explanation = prediction.get("llm_explanation") or prediction.get("clinical_summary")
        if explanation:
            story.append(Paragraph("Clinical Analysis & Patient Guidance", self.heading_style))
            # Safely format markdown for ReportLab Paragraph XML parser
            clean_text = html.escape(explanation)
            clean_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", clean_text)
            clean_text = re.sub(r"^#{1,6}\s*(.+?)$", r"<b>\1</b>", clean_text, flags=re.M)
            clean_text = re.sub(r"`(.+?)`", r"<i>\1</i>", clean_text)
            clean_text = clean_text.replace("\n\n", "<br/><br/>").replace("\n", "<br/>")
            story.append(Paragraph(clean_text, self.body_style))
            story.append(Spacer(1, 8))

        # 5. Longitudinal Visit History Table (if provided)
        if history and len(history) > 0:
            story.append(Paragraph("Longitudinal Visit History", self.heading_style))
            hist_rows = [["Visit Date", "Diagnosed Class", "Confidence", "Risk"]]
            for h in history[:5]:
                hist_date = h.get("date", "")[:10]
                hist_cls = h.get("class_name") or h.get("predicted_class", "—")
                hist_conf = f"{float(h.get('confidence', 0)) * 100:.1f}%"
                hist_risk = str(h.get("risk_level", "green")).upper()
                hist_rows.append([hist_date, hist_cls, hist_conf, hist_risk])

            hist_table = Table(hist_rows, colWidths=[1.8 * inch, 2.5 * inch, 1.5 * inch, 1.4 * inch])
            hist_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D47A1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B0BEC5")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(hist_table)
            story.append(Spacer(1, 10))

        # 6. Non-Removable Legal Disclaimer Footer
        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CFD8DC"), spaceAfter=6))
        story.append(Paragraph(
            "<b>MANDATORY MEDICAL DISCLAIMER:</b> This report is generated by an artificial intelligence assistant for educational and triage pre-screening purposes only. "
            "It does NOT constitute a formal medical diagnosis or treatment recommendation. Always bring this report to a licensed dermatologist for clinical verification.",
            self.disclaimer_style,
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def generate_pdf_base64(
        self,
        prediction: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        original_image_b64: Optional[str] = None,
        heatmap_b64: Optional[str] = None,
    ) -> str:
        """Return base64-encoded PDF string."""
        pdf_bytes = self.generate_pdf(prediction, history, original_image_b64, heatmap_b64)
        return base64.b64encode(pdf_bytes).decode("utf-8")
