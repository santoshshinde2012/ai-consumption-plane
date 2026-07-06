# Databricks notebook source
# MAGIC %pip install reportlab --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Generate synthetic E-Shop support documents into the Bronze volume.

Four PDFs are created so the unstructured half of the pipeline is testable
end to end. The complaint letter deliberately contains a fake email and
phone number so you can verify PII redaction in the Silver chunker.
Every evaluation question in 04_evaluation/eval_dataset.jsonl is answered
by exactly one of these documents.
Idempotent: files are overwritten on re-run.
"""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

import config

DOCS = {
    "return_policy.pdf": (
        "E-Shop Return Policy",
        [
            "1. General returns. Most items may be returned within 60 days of delivery for a full refund.",
            "2. Electronics. Electronics must be returned within 30 days of delivery and include all",
            "   original packaging and accessories. Opened software is not returnable.",
            "3. Refund method. Refunds are issued to the original payment method within 5 business days",
            "   of the returned item passing inspection at our warehouse.",
            "4. Exclusions. Gift cards, perishable goods, and customized items are final sale.",
        ],
    ),
    "shipping_faq.pdf": (
        "E-Shop Shipping FAQ",
        [
            "Q: Do you ship internationally?",
            "A: Yes. E-Shop ships to 45 countries. International orders typically arrive in 7 to 14",
            "   business days and may be subject to local customs duties payable by the recipient.",
            "Q: How much is standard domestic shipping?",
            "A: Standard shipping is free on orders over $50; otherwise a flat $5.99 applies.",
            "Q: Can I change my shipping address after ordering?",
            "A: Address changes are possible until the order status shows 'Shipped'.",
        ],
    ),
    "warranty_terms.pdf": (
        "E-Shop Limited Warranty Terms",
        [
            "All electronics sold by E-Shop include a 12-month limited manufacturer warranty covering",
            "defects in materials and workmanship under normal use.",
            "The warranty does not cover accidental damage, liquid damage, or unauthorized repairs.",
            "To make a claim, contact support with your order number; approved claims receive a repair,",
            "replacement, or refund at E-Shop's discretion within 10 business days.",
        ],
    ),
    "complaint_letter.pdf": (
        "Customer Complaint - Order 11396166",
        [
            "To whom it may concern,",
            "I am writing about order 11396166. The Model X-200 speaker arrived with a cracked casing.",
            "I request a replacement under warranty. You can reach me at jane.doe@example.com or on",
            "+1 415 555 0182 between 9am and 5pm.",
            "Severity: high. Product line: audio.",
            "Regards, Jane Doe",
        ],
    ),
}


def write_pdf(path: str, title: str, lines: list[str]) -> None:
    c = canvas.Canvas(path, pagesize=LETTER)
    width, height = LETTER
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, height - 1 * inch, title)
    c.setFont("Helvetica", 11)
    y = height - 1.4 * inch
    for line in lines:
        c.drawString(1 * inch, y, line)
        y -= 0.28 * inch
    c.showPage()
    c.save()


for filename, (title, lines) in DOCS.items():
    target = f"{config.DOCS_VOLUME_PATH}/{filename}"
    write_pdf(target, title, lines)
    print(f"wrote {target}")

print(f"\nDone. {len(DOCS)} PDFs in {config.DOCS_VOLUME_PATH} — run the pipeline next.")
