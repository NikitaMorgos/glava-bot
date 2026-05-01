import json, sys

with open("/opt/glava/exports/karakulina_v37_input_proofreader_checkpoint_20260430_064737.json") as f:
    book = json.load(f)

print("Top-level keys:", list(book.keys())[:10])

# Try to understand structure
if "chapters" in book:
    chs = book["chapters"]
    print("chapters count:", len(chs))
    ch0 = chs[0] if chs else {}
    print("chapter[0] keys:", list(ch0.keys())[:10])
    print("chapter[0] id:", ch0.get("id"))
    content = ch0.get("content", "")
    print("chapter[0] content (first 100):", repr(content[:100]))
    paragraphs = ch0.get("paragraphs", [])
    print("chapter[0] paragraphs count:", len(paragraphs))
    if paragraphs:
        print("paragraph[0] keys:", list(paragraphs[0].keys()))
        print("paragraph[0]:", paragraphs[0])
elif "content" in book:
    print("book.content keys:", list(book["content"].keys())[:5])
    chapters = book["content"].get("chapters", [])
    print("chapters count:", len(chapters))
    if chapters:
        print("chapter[0] keys:", list(chapters[0].keys()))
else:
    print("Unknown structure, full keys:", list(book.keys()))

# Now check prepare_book_for_layout output
sys.path.insert(0, "/opt/glava")
sys.path.insert(0, "/opt/glava/scripts")
from pipeline_utils import prepare_book_for_layout

prepared = prepare_book_for_layout(book)
print("\nprepared keys:", list(prepared.keys())[:5])
prep_chs = prepared.get("chapters", [])
print("prepared chapters:", len(prep_chs))
if prep_chs:
    c0 = prep_chs[0]
    print("prepared ch[0] keys:", list(c0.keys())[:10])
    c0_paras = c0.get("paragraphs", [])
    print("prepared ch[0] paragraphs:", len(c0_paras))
    if c0_paras:
        print("prepared ch[0] para[0]:", c0_paras[0])

from pdf_renderer import BookIndex
bi = BookIndex(prepared)
print("\nBookIndex._index type:", type(bi._index) if hasattr(bi, "_index") else "no _index")
if hasattr(bi, "_index"):
    print("BookIndex._index keys:", list(bi._index.keys())[:5])
