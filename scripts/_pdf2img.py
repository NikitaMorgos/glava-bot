from pdf2image import convert_from_path
pages = convert_from_path(
    "/opt/glava/exports/karakulina_stage4_pdf_iter1_20260404_091428.pdf",
    dpi=120, first_page=1, last_page=4
)
for i, p in enumerate(pages):
    p.save(f"/tmp/page_{i+1}.jpg", "JPEG", quality=88)
print("saved", len(pages), "pages")
