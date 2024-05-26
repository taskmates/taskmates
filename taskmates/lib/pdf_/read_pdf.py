from pypdf import PdfReader


def read_pdf(filename):
    reader = PdfReader(filename)

    pdf_texts = [p.extract_text().strip() for p in reader.pages]

    # Filter the empty strings
    pdf_texts = [text for text in pdf_texts if text]
    return "\n".join(pdf_texts)
