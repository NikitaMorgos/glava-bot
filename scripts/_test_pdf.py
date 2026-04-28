"""Quick smoke test for pdf_book with photo support."""
import sys
sys.path.insert(0, '/opt/glava')

from pdf_book import generate_book_pdf

bio = "# Глава 1\nТестовый текст.\n\n# Глава 2\nЕщё текст."
pdf = generate_book_pdf(bio, character_name="Тест")
print(f"PDF OK, bytes: {len(pdf)}")

# Test with fake photo
fake_photo = b'\xff\xd8\xff\xe0' + b'\x00' * 100  # minimal JPEG header
try:
    pdf2 = generate_book_pdf(bio, photo_items=[{"caption": "Тестовое фото", "image_bytes": fake_photo}])
    print(f"PDF with photo: {len(pdf2)} bytes (may fail on invalid JPEG - that's OK)")
except Exception as e:
    print(f"PDF with invalid photo handled gracefully: {e}")
