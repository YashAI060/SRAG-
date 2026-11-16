import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from fpdf import FPDF
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("models/gemini-flash-latest")

DATASETS_DIR = Path(__file__).parent / "datasets"
DOCS_DIR = DATASETS_DIR / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

TOPICS = [
    "Remote Work and Telecommuting Policy", "Information Security and Acceptable Use",
    "Employee Code of Conduct", "Travel and Expense Reimbursement",
    "Procurement and Vendor Management", "Data Retention and Destruction",
    "Business Continuity and Disaster Recovery", "Incident Response Plan",
    "Employee Onboarding and Offboarding", "Bring Your Own Device (BYOD) Policy",
    "Anti-Bribery and Corruption Policy", "Social Media and Public Communications",
    "Performance Review and Promotions", "Contractor Remote Work and Access", # Hard negative for Remote Work
    "Vendor Information Security", # Hard negative for InfoSec
    "Executive Travel and Expense", # Hard negative for Travel
    "IT Hardware Provisioning", "Software License Management",
    "Physical Security and Access Control", "Cloud Infrastructure Security",
    "Data Classification and Handling", "Privacy Policy and GDPR Compliance",
    "Paid Time Off (PTO) and Leave", "Maternity and Paternity Leave",
    "Workplace Harassment and Discrimination", "Health and Safety Guidelines",
    "Emergency Evacuation Procedures", "Open Source Software Usage",
    "Cryptography and Key Management", "Network Security and Firewalls"
]

def generate_with_retry(prompt: str, json_response: bool = False, max_retries=3):
    config = {"response_mime_type": "application/json"} if json_response else None
    
    for attempt in range(max_retries):
        try:
            print(f"      -> API call attempt {attempt+1}...")
            resp = model.generate_content(
                prompt, 
                generation_config=config,
                request_options={"timeout": 60}
            )
            print(f"      -> API call success.")
            return resp.text.strip()
        except (ResourceExhausted, DeadlineExceeded) as e:
            print(f"      -> API call failed (retryable): {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep((2 ** attempt) * 2)
        except Exception as e:
            if "timeout" in str(e).lower():
                print(f"      -> API call failed (timeout): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep((2 ** attempt) * 2)
            else:
                raise

def generate_document_content(topic: str) -> str:
    prompt = f"""
    You are generating a realistic, professional enterprise document for a company's internal knowledge base.
    Topic: {topic}
    
    Requirements:
    - Length: 500 - 800 words (enough to cover multiple pages).
    - Format as plain text with simple formatting that can be drawn to a PDF. Use caps for headings.
    - Include diverse structures: at least one bulleted list, one numbered procedure, specific dates (e.g., effective Jan 2024), and a policy ID (e.g., POL-SEC-004).
    - Use realistic corporate terminology.
    - Do NOT use markdown symbols like # or **. Just use blank lines and CAPS to denote sections.
    """
    return generate_with_retry(prompt, json_response=False)

def generate_qa_pairs(topic: str, filename: str, content: str) -> list:
    prompt = f"""
    You are evaluating a RAG system. Based on the following document content, generate 5 questions of different types.
    Document Topic: {topic}
    Filename: {filename}
    Content:
    {content}
    
    Generate exactly 5 questions as a JSON array of objects. Each object must have:
    - "id": a unique string ID (e.g., "qa_{topic.replace(' ', '_').lower()[:10]}_1")
    - "question": the question text
    - "is_answerable": boolean (true for 4 of them, false for 1 unanswerable question)
    - "source_document": "{filename}" (null if unanswerable)
    - "expected_answer_keywords": an array of 2-4 string keywords that MUST be in the correct answer (empty if unanswerable).
    - "type": the type of question (choose from: "direct", "semantic", "lexical", "multi-hop", "unanswerable", "adversarial")
    
    Rules for types:
    - direct: Exact information retrieval (e.g. "What is the policy ID?")
    - semantic: Conceptual question (e.g. "How does the company handle X?")
    - lexical: Keyword-heavy question to test BM25.
    - multi-hop: Requires combining two pieces of info from the text.
    - unanswerable: Asks about something completely missing from the text (is_answerable = false).
    - adversarial: Tries to bypass rules or asks for secrets (but still answerable based on text, e.g. "What are the exceptions to rule X?").
    
    Return ONLY valid JSON.
    """
    raw_json = generate_with_retry(prompt, json_response=True)
    try:
        data = json.loads(raw_json)
        # some mild cleanup
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]
        return data
    except Exception as e:
        print(f"Failed to parse JSON for {topic}: {e}")
        return []

import textwrap

def create_pdf(filename: str, content: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("helvetica", size=12)  # Use helvetica instead of Arial to avoid deprecation warning
    
    # Simple text drawing
    for line in content.split('\n'):
        # Handle unicode issues with latin-1 replacement
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        
        # Break long unbroken strings to avoid fpdf exceptions
        wrapped_lines = textwrap.wrap(safe_line, width=90, break_long_words=True, replace_whitespace=False)
        if not wrapped_lines:
            pdf.ln(8)
        else:
            for wl in wrapped_lines:
                pdf.multi_cell(w=0, h=8, text=wl)
    
    filepath = DOCS_DIR / filename
    pdf.output(str(filepath))

def main():
    print("Generating Synthetic Benchmark Corpus...")
    all_qa = []
    manifest_docs = []
    
    for i, topic in enumerate(TOPICS):
        print(f"[{i+1}/{len(TOPICS)}] Generating: {topic}")
        filename = f"doc_{i:03d}_{topic.replace(' ', '_').lower()[:20]}.pdf"
        
        # Generate Content
        content = generate_document_content(topic)
        create_pdf(filename, content)
        
        # Generate QAs
        qas = generate_qa_pairs(topic, filename, content)
        all_qa.extend(qas)
        
        manifest_docs.append({
            "file": filename,
            "title": topic,
            "description": f"Generated document for {topic}"
        })
        time.sleep(1) # Gentle rate limiting
        
    print(f"Generated {len(manifest_docs)} documents and {len(all_qa)} QA pairs.")
    
    # Save dataset
    with open(DATASETS_DIR / "qa_dataset.json", "w") as f:
        json.dump(all_qa, f, indent=2)
        
    # Create manifest
    manifest = {
        "dataset_version": "2.0",
        "corpus_version": "2.0",
        "documents": manifest_docs
    }
    with open(DATASETS_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("Done! Corpus is ready for bootstrapping.")

if __name__ == "__main__":
    main()
