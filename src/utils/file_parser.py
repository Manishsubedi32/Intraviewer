import io
from pdfminer.high_level import extract_text as extract_pdf
from docx import Document
from PIL import Image
import pytesseract


def extract_text_from_file(file_contents: bytes, filename: str) -> str:
    """Extract text from PDF, DOCX, TXT, or image (PNG/JPG)."""
    if not filename:
        raise ValueError("Filename is required to detect type")

    extension = filename.lower().split('.')[-1]

    if extension == "pdf":
        return extract_pdf(io.BytesIO(file_contents))
    
    elif extension == "docx":
        doc = Document(io.BytesIO(file_contents))
        return "\n".join([para.text for para in doc.paragraphs])
    
    elif extension == "txt":
        return file_contents.decode("utf-8", errors="replace")
    
    elif extension in ["png", "jpg", "jpeg"]:
        image = Image.open(io.BytesIO(file_contents))
        return pytesseract.image_to_string(image)
    
    else:
        raise ValueError(f"Unsupported file type: .{extension}")