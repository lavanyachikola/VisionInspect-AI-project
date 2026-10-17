import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image as RLImage)
from reportlab.lib.enums import TA_CENTER

def generate_pdf_report(inspection: dict, output_path: str) -> str:
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=15*mm, leftMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Title'],
                                     fontSize=22, textColor=colors.HexColor('#1e40af'),
                                     spaceAfter=10, alignment=TA_CENTER)
        h2_style = ParagraphStyle('H2', parent=styles['Heading2'],
                                  fontSize=13, textColor=colors.HexColor('#1e40af'),
                                  spaceBefore=12, spaceAfter=6)
        normal = styles['Normal']
        elements = []
        elements.append(Paragraph("VisionInspect AI", title_style))
        elements.append(Paragraph("Quality Inspection Report",
                                  ParagraphStyle('Sub', parent=normal, fontSize=12,
                                               alignment=TA_CENTER, textColor=colors.grey)))
        elements.append(Spacer(1, 10))
        decision = str(inspection.get("decision", "N/A"))
        if decision == "REJECT":
            bg_color, text_color = colors.HexColor('#fee2e2'), colors.HexColor('#991b1b')
        elif decision == "REWORK":
            bg_color, text_color = colors.HexColor('#fef3c7'), colors.HexColor('#92400e')
        else:
            bg_color, text_color = colors.HexColor('#dcfce7'), colors.HexColor('#166534')
        banner = Table([[Paragraph(f"<b>{decision}</b>",
                                   ParagraphStyle('Banner', parent=normal, fontSize=24,
                                                textColor=text_color, alignment=TA_CENTER))]],
                       colWidths=[180*mm])
        banner.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), bg_color),
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('TOPPADDING', (0, 0), (-1, -1), 15),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 15)]))
        elements.append(banner)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Product Information", h2_style))
        created = inspection.get("created_at", "")
        if hasattr(created, 'strftime'):
            created_str = created.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_str = str(created)[:19] if created else "N/A"
        info_data = [
            ["Inspection ID:", f"#{str(inspection.get('id', 'N/A'))[-8:]}"],
            ["Product:", str(inspection.get("product_name", "N/A"))],
            ["Product Code:", str(inspection.get("product_code", "N/A"))],
            ["Image Filename:", str(inspection.get("image_filename", "N/A"))],
            ["Date:", created_str],
        ]
        info_table = Table(info_data, colWidths=[50*mm, 130*mm])
        info_table.setStyle(TableStyle([('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        elements.append(info_table)
        if inspection.get("defect_detected"):
            elements.append(Paragraph("Defect Analysis", h2_style))
            defect_data = [
                ["Defect Type:", str(inspection.get("defect_type", "N/A"))],
                ["Confidence:", f"{int((inspection.get('confidence') or 0) * 100)}%"],
                ["Severity Score:", f"{inspection.get('severity_score', 0)}/100"],
                ["Severity Level:", str(inspection.get("severity_level", "None"))],
            ]
            loc = inspection.get("defect_location")
            if loc and isinstance(loc, dict):
                defect_data.append(["Location (X,Y):", f"({loc.get('x', 0)}, {loc.get('y', 0)})"])
                defect_data.append(["Size (W×H):", f"{loc.get('width', 0)}×{loc.get('height', 0)}"])
            defect_table = Table(defect_data, colWidths=[50*mm, 130*mm])
            defect_table.setStyle(TableStyle([('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                                              ('FONTSIZE', (0, 0), (-1, -1), 10),
                                              ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
            elements.append(defect_table)
        else:
            elements.append(Paragraph("No Defect Detected", h2_style))
            elements.append(Paragraph("Product meets all quality standards.", normal))
        qa = inspection.get("quality_analysis") or {}
        if qa and isinstance(qa, dict):
            elements.append(Paragraph("Image Quality Analysis", h2_style))
            res = qa.get('resolution', {}) or {}
            bri = qa.get('brightness', {}) or {}
            sha = qa.get('sharpness', {}) or {}
            noi = qa.get('noise', {}) or {}
            ovr = qa.get('overall', {}) or {}
            qa_data = [
                ["Resolution:", f"{res.get('width', 0)}×{res.get('height', 0)} ({res.get('status', 'N/A')})"],
                ["Brightness:", f"{bri.get('value', 0)} ({bri.get('status', 'N/A')})"],
                ["Sharpness:", f"{sha.get('value', 0)} ({sha.get('status', 'N/A')})"],
                ["Noise:", f"{noi.get('value', 0)} ({noi.get('status', 'N/A')})"],
                ["Overall Quality:", f"{ovr.get('score', 0)}% ({ovr.get('status', 'N/A')})"],
            ]
            qa_table = Table(qa_data, colWidths=[50*mm, 130*mm])
            qa_table.setStyle(TableStyle([('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                                          ('FONTSIZE', (0, 0), (-1, -1), 10),
                                          ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
            elements.append(qa_table)
        try:
            result_img_path = inspection.get("result_image_path")
            if result_img_path and os.path.exists(str(result_img_path)):
                elements.append(Paragraph("Detection Result Image", h2_style))
                img = RLImage(str(result_img_path), width=100*mm, height=100*mm)
                elements.append(img)
        except Exception as e:
            print(f"PDF image error: {e}")
        elements.append(Paragraph("Final Recommendation", h2_style))
        rec = str(inspection.get("recommendation", "N/A"))
        rec_table = Table([[Paragraph(rec, normal)]], colWidths=[180*mm])
        rec_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
                                       ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
                                       ('TOPPADDING', (0, 0), (-1, -1), 10),
                                       ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                                       ('LEFTPADDING', (0, 0), (-1, -1), 10)]))
        elements.append(rec_table)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                  ParagraphStyle('Footer', parent=normal, fontSize=8,
                                               textColor=colors.grey, alignment=TA_CENTER)))
        doc.build(elements)
        return output_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
