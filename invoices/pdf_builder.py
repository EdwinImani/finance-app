from decimal import Decimal
from io import BytesIO
from pathlib import Path

pdf_canvas = None

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_IMPORT_ERROR = None
except ImportError as exc:
    REPORTLAB_IMPORT_ERROR = exc


def build_invoice_pdf(*, invoice, company, items, importer, end_user, invoice_title, currency, document_type="default", packing_entries=None, **_ignored):
    if REPORTLAB_IMPORT_ERROR is not None:
        raise RuntimeError("ReportLab is not installed in the active Python environment.") from REPORTLAB_IMPORT_ERROR

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=14 * mm,
        topMargin=42 * mm,
        bottomMargin=42 * mm,
        title=invoice.invoice_number or invoice_title,
    )

    styles = _build_styles()
    story = []

    story.append(Spacer(1, 0))
    story.extend(_build_document_info(invoice, styles))
    story.append(Spacer(1, 3 * mm))
    story.extend(_build_partner_blocks(importer, end_user, styles))
    story.append(Spacer(1, 2 * mm))
    story.extend(_build_invoice_details(invoice, company, styles, document_type=document_type))
    story.append(Spacer(1, 6 * mm))
    page_totals = []
    if _is_shipping_document(document_type):
        story.extend(_build_shipping_document_intro(invoice, company, styles))
        story.append(Spacer(1, 4 * mm))
        item_pages = _split_items_for_pages(items, first_page_max=16, other_pages_max=20)
        for page_index, page_items in enumerate(item_pages):
            if page_index > 0:
                story.append(PageBreak())
                story.append(Spacer(1, 2 * mm))
            story.append(_build_shipping_items_table(page_items, styles))
            if page_index == len(item_pages) - 1:
                packing_section = _build_packing_section(
                    invoice=invoice,
                    packing_entries=packing_entries or [],
                    styles=styles,
                )
                if packing_section:
                    story.append(Spacer(1, 4 * mm))
                    story.extend(packing_section)
    else:
        item_pages = _split_items_for_pages(items, first_page_max=15, other_pages_max=17)
        page_totals = _compute_page_totals(
            invoice=invoice,
            item_pages=item_pages,
        )
        for page_index, page_items in enumerate(item_pages):
            if page_index > 0:
                story.append(PageBreak())
                story.append(Spacer(1, 2 * mm))
            story.append(_build_items_table(page_items, currency, styles))
            story.append(Spacer(1, 2 * mm))
            story.append(_build_page_totals_flowable(page_index, invoice, currency, styles, page_totals))

    def draw_page(canvas, doc):
        _draw_page_frame(
            canvas,
            doc,
            company=company,
            invoice=invoice,
            invoice_title=invoice_title,
            currency=currency,
            page_totals=page_totals,
            styles=styles,
        )

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def build_commercial_report_pdf(
    *,
    company,
    currency,
    invoices,
    chart_labels,
    chart_totals,
    total_qty,
    total_subtotal,
    total_vat,
    total_freight,
    total_discount,
    total_amount,
    from_date,
    to_date,
):
    if REPORTLAB_IMPORT_ERROR is not None:
        raise RuntimeError("ReportLab is not installed in the active Python environment.") from REPORTLAB_IMPORT_ERROR

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=14 * mm,
        topMargin=42 * mm,
        bottomMargin=42 * mm,
        title="Commercial Invoices Report",
    )

    styles = _build_styles()
    story = [
        Spacer(1, 0),
        Paragraph("<b>Report Period:</b> {} to {}".format(_escape(from_date or "-"), _escape(to_date or "-")), styles["body"]),
        Spacer(1, 2 * mm),
        _build_report_summary_table(
            currency=currency,
            total_qty=total_qty,
            total_subtotal=total_subtotal,
            total_vat=total_vat,
            total_freight=total_freight,
            total_discount=total_discount,
            total_amount=total_amount,
            styles=styles,
        ),
        Spacer(1, 5 * mm),
    ]

    chart = _build_commercial_report_chart(chart_labels, chart_totals)
    if chart is not None:
        story.extend(
            [
                Paragraph("Monthly Commercial Chart", styles["section_title"]),
                Spacer(1, 2 * mm),
                chart,
                Spacer(1, 5 * mm),
            ]
        )

    story.extend(
        [
            Paragraph("Commercial Invoices", styles["section_title"]),
            Spacer(1, 2 * mm),
            _build_commercial_report_table(invoices=invoices, currency=currency, styles=styles),
        ]
    )

    def draw_page(canvas, doc):
        _draw_report_page_frame(
            canvas,
            doc,
            company=company,
            report_title="Commercial Invoices Report",
            styles=styles,
        )

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def build_purchase_report_pdf(
    *,
    company,
    currency,
    purchase_orders,
    chart_labels,
    chart_totals,
    total_qty,
    total_gross,
    total_vat,
    total_freight,
    total_amount,
    from_date,
    to_date,
):
    if REPORTLAB_IMPORT_ERROR is not None:
        raise RuntimeError("ReportLab is not installed in the active Python environment.") from REPORTLAB_IMPORT_ERROR

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=14 * mm,
        topMargin=42 * mm,
        bottomMargin=42 * mm,
        title="Purchase Orders Report",
    )

    styles = _build_styles()
    story = [
        Spacer(1, 0),
        Paragraph("<b>Report Period:</b> {} to {}".format(_escape(from_date or "-"), _escape(to_date or "-")), styles["body"]),
        Spacer(1, 2 * mm),
        _build_purchase_report_summary_table(
            currency=currency,
            total_qty=total_qty,
            total_gross=total_gross,
            total_vat=total_vat,
            total_freight=total_freight,
            total_amount=total_amount,
            styles=styles,
        ),
        Spacer(1, 5 * mm),
    ]

    chart = _build_report_histogram(
        chart_labels=chart_labels,
        chart_totals=chart_totals,
        title="Monthly Purchase Chart",
    )
    if chart is not None:
        story.extend([chart, Spacer(1, 5 * mm)])

    story.extend(
        [
            Paragraph("Purchase Orders", styles["section_title"]),
            Spacer(1, 2 * mm),
            _build_purchase_report_table(purchase_orders=purchase_orders, currency=currency, styles=styles),
        ]
    )

    def draw_page(canvas, doc):
        _draw_report_page_frame(
            canvas,
            doc,
            company=company,
            report_title="Purchase Orders Report",
            styles=styles,
        )

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "InvoiceTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            textColor=colors.HexColor("#8A0F16"),
            spaceAfter=0,
        ),
        "section_title": ParagraphStyle(
            "SectionTitle",
            parent=base["Heading4"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            textColor=colors.HexColor("#B31217"),
            spaceAfter=0,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#7F1D1D"),
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
        ),
        "body_compact": ParagraphStyle(
            "BodyCompact",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=8,
            spaceBefore=0,
            spaceAfter=0,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
        ),
        "body_small": ParagraphStyle(
            "BodySmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
        ),
        "body_right": ParagraphStyle(
            "BodyRight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_RIGHT,
            textColor=colors.black,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#3F1D1D"),
        ),
        "table_cell_right": ParagraphStyle(
            "TableCellRight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#3F1D1D"),
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=9,
            alignment=TA_RIGHT,
            textColor=colors.black,
        ),
        "footer_left_small": ParagraphStyle(
            "FooterLeftSmall",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_LEFT,
            textColor=colors.black,
        ),
        "footer_center_small": ParagraphStyle(
            "FooterCenterSmall",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
            textColor=colors.black,
        ),
        "footer_right_small": ParagraphStyle(
            "FooterRightSmall",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_RIGHT,
            textColor=colors.black,
        ),
    }


def _build_document_info(invoice, styles):
    info_lines = [
        Paragraph(f"<b>Invoice Number:</b> {_escape(invoice.invoice_number or '-')}", styles["body"]),
        Paragraph(
            f"<b>Invoice Date:</b> {invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else '-'}",
            styles["body_compact"],
        ),
    ]
    return [Spacer(1, -2 * mm)] + info_lines


def _build_partner_blocks(importer, end_user, styles):
    importer_card = _partner_card("Importer", importer, styles)
    end_user_card = _partner_card("End User", end_user, styles)

    table = Table([[importer_card, end_user_card]], colWidths=[92 * mm, 92 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [table]


def _build_invoice_details(invoice, company, styles, document_type="default"):
    blocks = []

    invoice_note = getattr(company, "invoice_note", "") or "-"
    terms_lines = []
    if getattr(company, "terms_conditions", ""):
        terms_lines.append(f"<b>Terms and Conditions:</b> {_format_preserving_layout(company.terms_conditions)}")
    if getattr(company, "delivery_time", ""):
        terms_lines.append(f"<b>Delivery Time:</b> {_format_preserving_layout(company.delivery_time)}")
    if _is_proforma_invoice(invoice) and getattr(company, "proforma_validity", None):
        terms_lines.append(f"<b>Proforma Validity:</b> {_escape(company.proforma_validity)} days")
    note_box = _info_box("Invoice Note", _format_preserving_layout(invoice_note), styles)
    left_column = [note_box]

    if not _is_shipping_document(document_type):
        left_column.extend(
            [
                Spacer(1, 2 * mm),
                Paragraph(
                    f"<b>Our Reference:</b> {_format_preserving_layout(getattr(invoice, 'our_reference', '') or '-')}",
                    styles["body"],
                ),
            ]
        )

    if _is_shipping_document(document_type):
        right_column = []
    else:
        terms_text = "<br/>".join(terms_lines) if terms_lines else "-"
        terms_box = _info_box("Terms", terms_text, styles)

        if _is_proforma_invoice(invoice):
            price_for = getattr(invoice, "price_for", "") or "-"
            right_column = [
                terms_box,
                Spacer(1, 2 * mm),
                Paragraph(f"<b>Price for:</b> {_format_preserving_layout(price_for)}", styles["body"]),
            ]
        else:
            right_column = [terms_box]

    if not right_column:
        right_column = [Spacer(1, 0)]

    details_table = Table([[left_column, right_column]], colWidths=[92 * mm, 92 * mm], hAlign="LEFT")
    details_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    blocks.append(details_table)
    return blocks


def _build_shipping_document_intro(invoice, company, styles):
    left_column = [
        Paragraph(f"<b>Our Order No:</b> {_format_preserving_layout(getattr(invoice, 'our_order_no', '') or '-')}", styles["body"]),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Our Reference:</b> {_format_preserving_layout(getattr(invoice, 'our_reference', '') or '-')}", styles["body"]),
    ]

    right_note = getattr(invoice, "dispatching_note", "") or "-"
    right_column = [Paragraph(f"<b>Dispatching Note:</b> {_format_preserving_layout(right_note)}", styles["body_right"])]

    summary_table = Table([[left_column, right_column]], colWidths=[92 * mm, 92 * mm], hAlign="LEFT")
    summary_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [summary_table]


def _partner_card(title, partner, styles):
    lines = [Paragraph(title, styles["section_title"]), Spacer(1, 1 * mm)]

    name = partner.get("name") or "-"
    info_lines = [f"<b>{_escape(name)}</b>"]
    info_lines.extend(_escape(address) for address in partner.get("addresses", []) if address)

    phones = [phone for phone in partner.get("phones", []) if phone]
    if phones:
        info_lines.append(f"Tel: {_escape(', '.join(phones))}")
    if partner.get("email"):
        info_lines.append(f"Email: {_escape(partner['email'])}")
    if partner.get("website"):
        info_lines.append(_escape(partner["website"]))
    if partner.get("fax"):
        info_lines.append(f"Fax: {_escape(partner['fax'])}")

    lines.append(Paragraph("<br/>".join(info_lines), styles["body"]))
    card = Table([[lines]], colWidths=[89 * mm])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF5F5")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E5B8B8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    return card


def _info_box(title, text, styles):
    content = [
        Paragraph(title, styles["section_title"]),
        Spacer(1, 1 * mm),
        Paragraph(text if text == "-" else text, styles["body"]),
    ]
    box = Table([[content]], colWidths=[89 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF5F5")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E5B8B8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    return box


def _build_meta_section(invoice, company, styles):
    left_rows = [
        ["Order No", getattr(invoice, "our_order_no", "") or "-"],
        ["Currency", getattr(company, "currency", "") or "EUR"],
    ]

    if hasattr(invoice, "ready_for_report"):
        left_rows.append(["Validity", f"{getattr(company, 'proforma_validity', 0)} days"])

    right_rows = [
        ["Subtotal", _format_money(invoice.subtotal(), getattr(company, "currency", "EUR"))],
        ["VAT", f"{invoice.vat_percent:.2f}%"],
        ["Total", _format_money(invoice.total_amount(), getattr(company, "currency", "EUR"))],
    ]

    data = [
        [
            _meta_table(left_rows, styles),
            _meta_table(right_rows, styles, align_right=True),
        ]
    ]
    table = Table(data, colWidths=[85 * mm, 85 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [table]


def _meta_table(rows, styles, align_right=False):
    label_style = styles["label"]
    value_style = styles["body_right"] if align_right else styles["body"]
    table = Table(
        [[Paragraph(_escape(label), label_style), Paragraph(_escape(value), value_style)] for label, value in rows],
        colWidths=[24 * mm, 58 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E1E6EC")),
            ]
        )
    )
    return table


def _build_items_table(items, currency, styles):
    rows = [
        [
            Paragraph("Item", styles["table_head"]),
            Paragraph("Description", styles["table_head"]),
            Paragraph("Date", styles["table_head"]),
            Paragraph("Part No", styles["table_head"]),
            Paragraph("HS Code", styles["table_head"]),
            Paragraph("Qty", styles["table_head"]),
            Paragraph("Unit Price", styles["table_head"]),
            Paragraph("Amount", styles["table_head"]),
        ]
    ]

    for item in items:
        rows.append(
            [
                Paragraph(str(item["index"]), styles["table_cell"]),
                Paragraph(_escape(item["description"]), styles["table_cell"]),
                Paragraph(_escape(item["item_date"]), styles["table_cell"]),
                Paragraph(_escape(item["part_number"]), styles["table_cell"]),
                Paragraph(_escape(item["hs_code"]), styles["table_cell"]),
                Paragraph(str(item["quantity"]), styles["table_cell_right"]),
                Paragraph(_format_money(item["unit_price"], currency), styles["table_cell_right"]),
                Paragraph(_format_money(item["total_amount"], currency), styles["table_cell_right"]),
            ]
        )

    if len(rows) == 1:
        rows.append(
            [
                Paragraph("-", styles["table_cell"]),
                Paragraph("No items", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell_right"]),
                Paragraph("-", styles["table_cell_right"]),
                Paragraph("-", styles["table_cell_right"]),
            ]
        )

    table = Table(
        rows,
        colWidths=[10 * mm, 48 * mm, 20 * mm, 23 * mm, 18 * mm, 12 * mm, 25 * mm, 24 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A61B1B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5B8B8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF5F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_shipping_items_table(items, styles):
    rows = [
        [
            Paragraph("Item No.", styles["table_head"]),
            Paragraph("Description", styles["table_head"]),
            Paragraph("Part Number", styles["table_head"]),
            Paragraph("Qty", styles["table_head"]),
        ]
    ]

    for item in items:
        rows.append(
            [
                Paragraph(str(item["index"]), styles["table_cell"]),
                Paragraph(_escape(item["description"]), styles["table_cell"]),
                Paragraph(_escape(item["part_number"]), styles["table_cell"]),
                Paragraph(str(item["quantity"]), styles["table_cell_right"]),
            ]
        )

    if len(rows) == 1:
        rows.append(
            [
                Paragraph("-", styles["table_cell"]),
                Paragraph("No items", styles["table_cell"]),
                Paragraph("-", styles["table_cell"]),
                Paragraph("-", styles["table_cell_right"]),
            ]
        )

    table = Table(
        rows,
        colWidths=[18 * mm, 96 * mm, 42 * mm, 28 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A61B1B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5B8B8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF5F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_packing_section(*, invoice, packing_entries, styles):
    specification = getattr(invoice, "packing_specification", "") or "-"
    if not packing_entries and specification == "-":
        return []

    blocks = [
        Paragraph(f"<b>Packing Specification:</b> {_format_preserving_layout(specification)}", styles["body"]),
        Spacer(1, 3 * mm),
    ]

    header_top = [
        Paragraph("Item No.", styles["table_head"]),
        Paragraph("No Packing", styles["table_head"]),
        Paragraph("Gross", styles["table_head"]),
        Paragraph("Net", styles["table_head"]),
        Paragraph("L", styles["table_head"]),
        Paragraph("W", styles["table_head"]),
        Paragraph("H", styles["table_head"]),
    ]
    rows = [header_top]

    for entry in packing_entries:
        rows.append(
            [
                Paragraph(str(entry["index"]), styles["table_cell"]),
                Paragraph(_escape(entry["no_packing"]), styles["table_cell"]),
                Paragraph(_format_plain_decimal(entry["gross_weight"]), styles["table_cell_right"]),
                Paragraph(_format_plain_decimal(entry["net_weight"]), styles["table_cell_right"]),
                Paragraph(_format_plain_decimal(entry["dimension_length"]), styles["table_cell_right"]),
                Paragraph(_format_plain_decimal(entry["dimension_width"]), styles["table_cell_right"]),
                Paragraph(_format_plain_decimal(entry["dimension_height"]), styles["table_cell_right"]),
            ]
        )

    if len(rows) == 1:
        rows.append(
            [
                Paragraph("-", styles["table_cell"]),
                Paragraph("No packing entries", styles["table_cell"]),
                Paragraph("-", styles["table_cell_right"]),
                Paragraph("-", styles["table_cell_right"]),
                Paragraph("-", styles["table_cell_right"]),
                Paragraph("-", styles["table_cell_right"]),
                Paragraph("-", styles["table_cell_right"]),
            ]
        )

    packing_table = Table(
        rows,
        colWidths=[16 * mm, 84 * mm, 18 * mm, 18 * mm, 16 * mm, 16 * mm, 16 * mm],
        repeatRows=1,
    )
    packing_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A61B1B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5B8B8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF5F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    blocks.append(packing_table)
    return blocks


def _build_totals_table(invoice, currency, styles):
    return _build_totals_table_from_values(
        gross_value=invoice.subtotal(),
        freight=invoice.freight,
        vat_amount=invoice.vat_amount(),
        discount=invoice.discount,
        total_amount=invoice.total_amount(),
        currency=currency,
        styles=styles,
    )


def _build_totals_table_from_values(*, gross_value, freight, vat_amount, discount, total_amount, currency, styles, extra_rows=None):
    rows = [
        ["Gross Value", _format_money(gross_value, currency)],
        ["Freight", _format_money(freight, currency)],
        ["Vat Amount", _format_money(vat_amount, currency)],
        ["Discount", _format_money(discount, currency)],
        ["Total Amount", _format_money(total_amount, currency)],
    ]
    if extra_rows:
        rows.extend([[label, _format_money(value, currency)] for label, value in extra_rows])
    cells = [
        [Paragraph(_escape(label), styles["label"]), Paragraph(_escape(value), styles["body_right"])]
        for label, value in rows
    ]
    table = Table(cells, colWidths=[35 * mm, 35 * mm], hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#FDECEC")),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor("#D8A1A1")),
                ("LINEABOVE", (0, 4), (-1, 4), 0.8, colors.HexColor("#B31217")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_notes_text(invoice, company):
    notes = []
    invoice_note = getattr(company, "invoice_note", "")
    if invoice_note:
        notes.append(invoice_note)

    terms = getattr(company, "terms_conditions", "")
    if terms:
        notes.append(f"Terms: {terms}")

    delivery = getattr(company, "delivery_time", "")
    if delivery:
        notes.append(f"Delivery: {delivery}")

    footer_invoice = getattr(company, "footer_invoice", "")
    if footer_invoice:
        notes.append(footer_invoice)

    return "<br/><br/>".join(_escape(note) for note in notes if note)


def _build_footer_left_text(invoice, company):
    footer_parts = _clean_lines(
        f"Bank: {company.bank}" if getattr(company, "bank", "") else "",
        f"IBAN: {company.iban}" if getattr(company, "iban", "") else "",
        f"BIC: {company.bic}" if getattr(company, "bic", "") else "",
    )
    return "<br/>".join(_escape(part) for part in footer_parts)


def _build_footer_center_text(invoice, company):
    footer_invoice = getattr(company, "footer_invoice", "") or ""
    parts = [part.strip() for part in str(footer_invoice).split("_") if part.strip()]
    return "<br/>".join(_escape(part) for part in parts)


def _build_footer_right_text(invoice, company):
    footer_parts = _clean_lines(
        f"Telephone: {company.company_phone}" if getattr(company, "company_phone", "") else "",
        f"Fax: {company.company_fax}" if getattr(company, "company_fax", "") else "",
        f"Email: {company.company_email}" if getattr(company, "company_email", "") else "",
    )
    return "<br/>".join(_escape(part) for part in footer_parts)


def _is_commercial_invoice(invoice):
    return invoice.__class__.__name__ == "CommercialInvoice"


def _is_proforma_invoice(invoice):
    return invoice.__class__.__name__ == "ProformaInvoice"


def _is_shipping_document(document_type):
    return document_type in {"packing_list", "dispatching_note"}


def _draw_page_frame(canvas, document, *, company, invoice, invoice_title, currency, page_totals, styles):
    canvas.saveState()

    _draw_page_header(canvas, document, company, invoice, invoice_title, styles)
    _draw_page_footer(canvas, document, invoice, company, styles)
    canvas.restoreState()


def _draw_report_page_frame(canvas, document, *, company, report_title, styles):
    canvas.saveState()
    left_x = document.leftMargin
    top_y = document.pagesize[1] - 12 * mm

    company_name = Paragraph(_escape(getattr(company, "company_name", "") or "Company"), styles["title"])
    company_name.wrapOn(canvas, 110 * mm, 10 * mm)
    company_name.drawOn(canvas, left_x, top_y - 10 * mm)

    report_type = Paragraph(_escape((report_title or "").upper()), styles["section_title"])
    report_type.wrapOn(canvas, 90 * mm, 6 * mm)
    report_type.drawOn(canvas, left_x, top_y - 18 * mm)

    logo_path = getattr(getattr(company, "company_logo", None), "path", "")
    if logo_path and Path(logo_path).exists():
        logo_width = 22 * mm
        logo_height = 14 * mm
        logo_x = document.pagesize[0] - document.rightMargin - logo_width
        logo_y = top_y - 14 * mm
        canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask="auto")

    _draw_page_footer(canvas, document, None, company, styles)
    canvas.restoreState()


def _draw_page_header(canvas, document, company, invoice, invoice_title, styles):
    left_x = document.leftMargin
    top_y = document.pagesize[1] - 12 * mm
    page_number = canvas.getPageNumber()

    company_name = Paragraph(_escape(getattr(company, "company_name", "") or "Company"), styles["title"])
    company_name.wrapOn(canvas, 110 * mm, 10 * mm)
    company_name.drawOn(canvas, left_x, top_y - 10 * mm)

    invoice_type = Paragraph(_escape((invoice_title or "").upper()), styles["section_title"])
    invoice_type.wrapOn(canvas, 80 * mm, 6 * mm)
    invoice_type.drawOn(canvas, left_x, top_y - 18 * mm)

    if page_number > 1:
        invoice_meta = Paragraph(
            (
                f"<b>Invoice Number:</b> {_escape(invoice.invoice_number or '-')}<br/>"
                f"<b>Invoice Date:</b> {invoice.invoice_date.strftime('%d/%m/%Y') if invoice.invoice_date else '-'}"
            ),
            styles["body_small"],
        )
        invoice_meta.wrapOn(canvas, 55 * mm, 10 * mm)
        invoice_meta.drawOn(canvas, left_x, top_y - 28 * mm)

    logo_path = getattr(getattr(company, "company_logo", None), "path", "")
    if logo_path and Path(logo_path).exists():
        logo_width = 22 * mm
        logo_height = 14 * mm
        logo_x = document.pagesize[0] - document.rightMargin - logo_width
        logo_y = top_y - 14 * mm
        canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask="auto")


def _draw_page_footer(canvas, document, invoice, company, styles):
    footer_left = _build_footer_left_text(invoice, company)
    footer_center = _build_footer_center_text(invoice, company)
    footer_right = _build_footer_right_text(invoice, company)
    if not any([footer_left, footer_center, footer_right]):
        return

    available_width = document.width
    footer_table = Table(
        [[
            Paragraph(footer_left or "", styles["footer_left_small"]),
            Paragraph(footer_center or "", styles["footer_center_small"]),
            Paragraph(footer_right or "", styles["footer_right_small"]),
        ]],
        colWidths=[available_width * 0.3, available_width * 0.4, available_width * 0.3],
    )
    footer_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    footer_width, footer_height = footer_table.wrap(document.width, 12 * mm)
    footer_table.drawOn(canvas, document.leftMargin, 11 * mm)


def _build_page_totals_flowable(page_index, invoice, currency, styles, page_totals):
    if not page_totals:
        return Spacer(1, 0)

    summary = page_totals[page_index]
    is_last_page = page_index == len(page_totals) - 1
    detail_table = _build_page_gross_values_table(summary["page_cumulative_gross_values"], currency, styles)

    if is_last_page:
        totals_table = _build_totals_table_from_values(
            gross_value=summary["all_pages_gross_value"],
            freight=Decimal(getattr(invoice, "freight", 0) or 0),
            vat_amount=(summary["all_pages_gross_value"] * Decimal(getattr(invoice, "vat_percent", 0) or 0)) / Decimal("100"),
            discount=Decimal(getattr(invoice, "discount", 0) or 0),
            total_amount=summary["all_pages_total"],
            currency=currency,
            styles=styles,
        )
        if len(page_totals) == 1:
            return totals_table

        wrapper = Table([[[detail_table, Spacer(1, 2 * mm), totals_table]]], colWidths=[70 * mm], hAlign="RIGHT")
        wrapper.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return wrapper

    return detail_table


def _format_money(value, currency):
    amount = Decimal(value or 0).quantize(Decimal("0.01"))
    return f"{amount:,.2f} {currency}"


def _format_plain_decimal(value):
    amount = Decimal(value or 0).quantize(Decimal("0.01"))
    return f"{amount:,.2f}"


def _clean_lines(*values):
    lines = []
    for value in values:
        if not value:
            continue
        for line in str(value).splitlines():
            cleaned = line.strip()
            if cleaned:
                lines.append(cleaned)
    return lines


def _escape(value):
    return (
        str(value or "-")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_preserving_layout(value):
    escaped = _escape(value)
    escaped = escaped.replace("  ", "&nbsp; ")
    return escaped.replace("\n", "<br/>")


def _compute_page_totals(*, invoice, item_pages):
    if not item_pages:
        return []

    results = []
    cumulative_gross_value = Decimal("0.00")
    vat_percent = getattr(invoice, "vat_percent", Decimal("0.00")) or Decimal("0.00")
    all_pages_gross_value = sum(
        (sum((Decimal(item["total_amount"]) for item in page_items), Decimal("0.00")) for page_items in item_pages),
        Decimal("0.00"),
    )
    all_pages_total = all_pages_gross_value + (all_pages_gross_value * Decimal(vat_percent)) / Decimal("100") + Decimal(getattr(invoice, "freight", 0) or 0) - Decimal(getattr(invoice, "discount", 0) or 0)
    page_gross_values = []
    page_cumulative_gross_values = []

    for page_items in item_pages:
        page_total = sum((Decimal(item["total_amount"]) for item in page_items), Decimal("0.00"))
        page_gross_values.append(page_total)
        cumulative_gross_value += page_total
        page_cumulative_gross_values.append(cumulative_gross_value)

        gross_value = cumulative_gross_value
        freight = Decimal(getattr(invoice, "freight", 0) or 0)
        discount = Decimal(getattr(invoice, "discount", 0) or 0)

        vat_amount = (gross_value * Decimal(vat_percent)) / Decimal("100")
        total_amount = gross_value + vat_amount + freight - discount

        results.append(
            {
                "gross_value": gross_value,
                "freight": freight,
                "vat_amount": vat_amount,
                "discount": discount,
                "total_amount": total_amount,
                "page_item_total": page_total,
                "cumulative_gross_value": cumulative_gross_value,
                "all_pages_gross_value": all_pages_gross_value,
                "all_pages_total": all_pages_total,
                "page_gross_values": list(page_gross_values),
                "page_cumulative_gross_values": list(page_cumulative_gross_values),
            }
        )

    return results


def _build_page_gross_values_table(page_gross_values, currency, styles):
    rows = [
        [Paragraph(_escape(f"Page {index} Gross Value"), styles["label"]), Paragraph(_format_money(value, currency), styles["body_right"])]
        for index, value in enumerate(page_gross_values, start=1)
    ]
    table = Table(rows, colWidths=[35 * mm, 35 * mm], hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor("#D8A1A1")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_report_summary_table(*, currency, total_qty, total_subtotal, total_vat, total_freight, total_discount, total_amount, styles):
    rows = [
        ["Total Quantity", str(total_qty)],
        ["Subtotal", _format_money(total_subtotal, currency)],
        ["VAT", _format_money(total_vat, currency)],
        ["Freight", _format_money(total_freight, currency)],
        ["Discount", _format_money(total_discount, currency)],
        ["Total Amount", _format_money(total_amount, currency)],
    ]
    cells = [
        [Paragraph(_escape(label), styles["label"]), Paragraph(_escape(value), styles["body_right"])]
        for label, value in rows
    ]
    table = Table(cells, colWidths=[40 * mm, 40 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#FDECEC")),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor("#D8A1A1")),
                ("LINEABOVE", (0, 5), (-1, 5), 0.8, colors.HexColor("#B31217")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_purchase_report_summary_table(*, currency, total_qty, total_gross, total_vat, total_freight, total_amount, styles):
    rows = [
        ["Total Quantity", str(total_qty)],
        ["Gross Value", _format_money(total_gross, currency)],
        ["VAT", _format_money(total_vat, currency)],
        ["Freight", _format_money(total_freight, currency)],
        ["Total Amount", _format_money(total_amount, currency)],
    ]
    cells = [
        [Paragraph(_escape(label), styles["label"]), Paragraph(_escape(value), styles["body_right"])]
        for label, value in rows
    ]
    table = Table(cells, colWidths=[40 * mm, 40 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#FDECEC")),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor("#D8A1A1")),
                ("LINEABOVE", (0, 4), (-1, 4), 0.8, colors.HexColor("#B31217")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _build_report_histogram(*, chart_labels, chart_totals, title):
    if not chart_labels or not chart_totals:
        return None

    drawing = Drawing(180 * mm, 78 * mm)
    chart = VerticalBarChart()
    chart.x = 18 * mm
    chart.y = 12 * mm
    chart.height = 48 * mm
    chart.width = 150 * mm
    chart.data = [chart_totals]
    chart.categoryAxis.categoryNames = [str(label) for label in chart_labels]
    chart.categoryAxis.labels.angle = 0
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.dy = -6
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7.5
    chart.valueAxis.valueMin = 0
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = colors.HexColor("#D9D9D9")
    chart.valueAxis.gridStrokeWidth = 0.5
    chart.categoryAxis.strokeColor = colors.HexColor("#CFCFCF")
    chart.valueAxis.strokeColor = colors.HexColor("#CFCFCF")
    chart.categoryAxis.labels.fillColor = colors.HexColor("#5F6368")
    chart.valueAxis.labels.fillColor = colors.HexColor("#5F6368")
    chart.groupSpacing = 0
    chart.barSpacing = 0

    palette = [
        (colors.HexColor("#5C9F7D"), colors.HexColor("#3E7A5D")),
        (colors.HexColor("#648FAE"), colors.HexColor("#416C8B")),
        (colors.HexColor("#EDCB73"), colors.HexColor("#C5A24A")),
        (colors.HexColor("#EA7D61"), colors.HexColor("#C65E43")),
        (colors.HexColor("#B78EC8"), colors.HexColor("#8A63A0")),
        (colors.HexColor("#57A39C"), colors.HexColor("#347D76")),
    ]
    for index, _ in enumerate(chart_totals):
        fill, stroke = palette[index % len(palette)]
        chart.bars[(0, index)].fillColor = fill
        chart.bars[(0, index)].strokeColor = stroke
        chart.bars[(0, index)].strokeWidth = 0.8

    drawing.add(chart)
    drawing.add(String(0, 70 * mm, title, fontName="Helvetica-Bold", fontSize=13, fillColor=colors.HexColor("#8A0F16")))
    drawing.add(String(0, 64 * mm, "Metric: Total Amount", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.HexColor("#5F6368")))
    drawing.add(String(90 * mm, 4 * mm, "Month", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#5F6368"), textAnchor="middle"))
    return drawing


def _build_commercial_report_chart(chart_labels, chart_totals):
    return _build_report_histogram(
        chart_labels=chart_labels,
        chart_totals=chart_totals,
        title="Monthly Commercial Chart",
    )


def _build_commercial_report_table(*, invoices, currency, styles):
    rows = [[
        Paragraph("Date", styles["table_head"]),
        Paragraph("Number", styles["table_head"]),
        Paragraph("Importer", styles["table_head"]),
        Paragraph("End User", styles["table_head"]),
        Paragraph("Qty", styles["table_head"]),
        Paragraph("Subtotal", styles["table_head"]),
        Paragraph("VAT", styles["table_head"]),
        Paragraph("Freight", styles["table_head"]),
        Paragraph("Discount", styles["table_head"]),
        Paragraph("Total", styles["table_head"]),
    ]]

    for invoice in invoices:
        rows.append(
            [
                Paragraph(invoice.invoice_date.strftime("%d/%m/%Y") if invoice.invoice_date else "-", styles["table_cell"]),
                Paragraph(_escape(invoice.invoice_number or "-"), styles["table_cell"]),
                Paragraph(_escape(getattr(invoice.importer, "description", "-") or "-"), styles["table_cell"]),
                Paragraph(_escape(getattr(invoice.end_user, "description", "-") or "-"), styles["table_cell"]),
                Paragraph(_escape(invoice.qty_total or 0), styles["table_cell_right"]),
                Paragraph(_format_money(getattr(invoice, "subtotal_db", 0), currency), styles["table_cell_right"]),
                Paragraph(_format_money(invoice.vat_amount(), currency), styles["table_cell_right"]),
                Paragraph(_format_money(invoice.freight, currency), styles["table_cell_right"]),
                Paragraph(_format_money(invoice.discount, currency), styles["table_cell_right"]),
                Paragraph(_format_money(invoice.total_amount(), currency), styles["table_cell_right"]),
            ]
        )

    if len(rows) == 1:
        rows.append([Paragraph("-", styles["table_cell"])] * 10)

    table = Table(
        rows,
        colWidths=[18 * mm, 24 * mm, 33 * mm, 33 * mm, 14 * mm, 18 * mm, 16 * mm, 16 * mm, 16 * mm, 18 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A61B1B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5B8B8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF5F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_purchase_report_table(*, purchase_orders, currency, styles):
    rows = [[
        Paragraph("Date", styles["table_head"]),
        Paragraph("Number", styles["table_head"]),
        Paragraph("Seller", styles["table_head"]),
        Paragraph("Requester", styles["table_head"]),
        Paragraph("Qty", styles["table_head"]),
        Paragraph("Gross", styles["table_head"]),
        Paragraph("VAT", styles["table_head"]),
        Paragraph("Freight", styles["table_head"]),
        Paragraph("Total", styles["table_head"]),
    ]]

    for po in purchase_orders:
        rows.append(
            [
                Paragraph(po.purchase_date.strftime("%d/%m/%Y") if po.purchase_date else "-", styles["table_cell"]),
                Paragraph(_escape(po.purchase_number or "-"), styles["table_cell"]),
                Paragraph(_escape(getattr(po.seller, "description", "-") or "-"), styles["table_cell"]),
                Paragraph(_escape(getattr(po.requester, "description", "-") or "-"), styles["table_cell"]),
                Paragraph(_escape(po.qty_total or 0), styles["table_cell_right"]),
                Paragraph(_format_money(getattr(po, "gross_value_db", 0), currency), styles["table_cell_right"]),
                Paragraph(_format_money(po.vat_amount(), currency), styles["table_cell_right"]),
                Paragraph(_format_money(po.freight, currency), styles["table_cell_right"]),
                Paragraph(_format_money(po.total_amount(), currency), styles["table_cell_right"]),
            ]
        )

    if len(rows) == 1:
        rows.append([Paragraph("-", styles["table_cell"])] * 9)

    table = Table(
        rows,
        colWidths=[18 * mm, 28 * mm, 40 * mm, 40 * mm, 14 * mm, 18 * mm, 16 * mm, 16 * mm, 18 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#A61B1B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5B8B8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF5F5")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table




def _split_items_for_pages(items, *, first_page_max, other_pages_max):
    if not items:
        return [[]]

    pages = [items[:first_page_max]]
    remaining = items[first_page_max:]
    while remaining:
        pages.append(remaining[:other_pages_max])
        remaining = remaining[other_pages_max:]
    return pages


if pdf_canvas is not None:
    class NumberedCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []
            self.page_count = 0

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            self._saved_page_states.append(dict(self.__dict__))
            page_states = list(self._saved_page_states)
            total_pages = max(1, len(page_states) - 1)
            self.page_count = total_pages

            for index, state in enumerate(page_states[:-1], start=1):
                self.__dict__.update(state)
                self.page_count = total_pages
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#6C7682"))
                self.drawCentredString(
                    self._pagesize[0] / 2,
                    8 * mm,
                    f"page {index} of {total_pages}",
                )
                super().showPage()
            super().save()
