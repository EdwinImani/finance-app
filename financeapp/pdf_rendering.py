import ctypes.util
import os
import platform


WINDOWS_WEASYPRINT_LIBRARIES = (
    "libgobject-2.0-0",
    "gobject-2.0-0",
    "libpango-1.0-0",
    "pango-1.0-0",
    "libharfbuzz-0",
    "harfbuzz-0",
)


def should_try_weasyprint():
    renderer = os.getenv("PDF_RENDERER", "").strip().lower()
    if renderer == "xhtml2pdf":
        return False
    if renderer == "weasyprint":
        return True

    if platform.system() != "Windows":
        return True

    return all(ctypes.util.find_library(library) for library in WINDOWS_WEASYPRINT_LIBRARIES)


def get_pdf_fallback_reason():
    renderer = os.getenv("PDF_RENDERER", "").strip().lower()
    if renderer == "xhtml2pdf":
        return "PDF_RENDERER=xhtml2pdf is set."

    if platform.system() != "Windows":
        return ""

    missing_libraries = [
        library
        for library in WINDOWS_WEASYPRINT_LIBRARIES
        if not ctypes.util.find_library(library)
    ]
    if not missing_libraries:
        return ""

    return (
        "WeasyPrint native Windows libraries are missing "
        f"({', '.join(missing_libraries)})."
    )
