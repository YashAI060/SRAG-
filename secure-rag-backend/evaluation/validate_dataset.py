import json
from pathlib import Path

DATASETS_DIR = Path(__file__).parent / "datasets"

def validate():
    with open(DATASETS_DIR / "manifest.json") as f:
        manifest = json.load(f)
        
    with open(DATASETS_DIR / "qa_dataset.json") as f:
        qa_data = json.load(f)
        
    import fitz  # PyMuPDF

    docs = {d["file"] for d in manifest["documents"]}
    
    errors = []
    ids = set()
    
    # 1. Check physical PDF existence and validity
    pdf_count = 0
    for doc in docs:
        filepath = DATASETS_DIR / "documents" / doc
        if not filepath.exists():
            errors.append(f"Document missing from disk: {doc}")
            continue
        try:
            with fitz.open(filepath) as f:
                if len(f) < 1:
                    errors.append(f"Document has 0 pages: {doc}")
            pdf_count += 1
        except Exception as e:
            errors.append(f"Malformed PDF: {doc} - {e}")
            
    if pdf_count < 30:
        errors.append(f"Expected at least 30 PDFs, found {pdf_count}.")
    
    # 2. Check QA pairs
    for idx, q in enumerate(qa_data):
        qid = q.get("id")
        if not qid:
            errors.append(f"Row {idx}: missing id")
        elif qid in ids:
            errors.append(f"Row {idx}: duplicate id {qid}")
        else:
            ids.add(qid)
            
        src_doc = q.get("source_document")
        is_ans = q.get("is_answerable")
        
        if is_ans:
            if not src_doc:
                errors.append(f"Q {qid}: answerable but missing source_document")
            elif src_doc not in docs:
                errors.append(f"Q {qid}: source_document {src_doc} not in manifest")
                
            keywords = q.get("expected_answer_keywords")
            if not keywords or not isinstance(keywords, list):
                errors.append(f"Q {qid}: missing or invalid expected_answer_keywords")
        else:
            if src_doc:
                errors.append(f"Q {qid}: unanswerable but has source_document {src_doc}")
            keywords = q.get("expected_answer_keywords")
            if keywords:
                errors.append(f"Q {qid}: unanswerable but has keywords {keywords}")
                
    if errors:
        print("❌ Validation failed with errors:")
        for e in errors:
            print(f"  - {e}")
        return False
        
    print(f"✅ Validation passed! {len(qa_data)} questions validated across {len(docs)} documents.")
    return True

if __name__ == "__main__":
    validate()
