import re


UNSAFE_FILENAME_CHARACTERS = re.compile(r'[/\\:*?"<>|]')


def safe_filename(value):
    """Return a document number that is safe inside a download filename."""
    return UNSAFE_FILENAME_CHARACTERS.sub("-", str(value or "").strip())


def document_pdf_filename(document_type, document_number):
    safe_number = safe_filename(document_number) or "document"
    return f"{document_type}-{safe_number}.pdf"
