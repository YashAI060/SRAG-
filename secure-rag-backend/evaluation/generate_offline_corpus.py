import json
import random
from pathlib import Path
from fpdf import FPDF
import textwrap

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
    "Performance Review and Promotions", "Contractor Remote Work and Access", 
    "Vendor Information Security", "Executive Travel and Expense", 
    "IT Hardware Provisioning", "Software License Management",
    "Physical Security and Access Control", "Cloud Infrastructure Security",
    "Data Classification and Handling", "Privacy Policy and GDPR Compliance",
    "Paid Time Off (PTO) and Leave", "Maternity and Paternity Leave",
    "Workplace Harassment and Discrimination", "Health and Safety Guidelines",
    "Emergency Evacuation Procedures", "Open Source Software Usage",
    "Cryptography and Key Management", "Network Security and Firewalls"
]

def generate_offline_content_and_qas(topic: str, idx: int, filename: str):
    # Deterministic generation
    random.seed(idx)
    
    # 3 distinct facts to embed
    fact_1 = f"{random.randint(1, 30)} days"
    fact_2 = f"{random.choice(['VP', 'Director', 'Manager', 'HR'])} approval"
    fact_3 = f"POL-{topic.replace(' ', '')[:3].upper()}-{idx:03d}"
    
    # Generate generic boilerplate text to expand document length
    filler_paragraphs = [
        "The company is committed to maintaining the highest standards of operational excellence. All procedures described herein are subject to continuous review and improvement. Employees are expected to familiarize themselves with these guidelines and apply them diligently in their daily operations. Failure to comply may result in a review by the appropriate oversight committee.",
        "In addition to the primary directives, this section outlines supplementary protocols. These protocols are designed to ensure consistency across all departments. Managers are responsible for ensuring their teams are trained on these procedures. Regular training sessions will be scheduled to address any questions or concerns.",
        "Data privacy and confidentiality are paramount. All information handled under this policy must be treated with the utmost care. Unauthorized disclosure of sensitive information is strictly prohibited. Employees must use approved communication channels for all official correspondence.",
        "To facilitate effective implementation, a phased approach will be adopted. Phase one involves initial communication and training. Phase two focuses on integration into existing workflows. Finally, phase three consists of a comprehensive audit to measure compliance and identify areas for improvement.",
        "Resource allocation for these initiatives will be managed centrally. Department heads must submit their requirements by the end of the first quarter. Requests will be prioritized based on strategic alignment and potential impact. Approval is contingent upon budget availability.",
        "Exceptions to this policy may be granted under extraordinary circumstances. Requests for exceptions must be submitted in writing, detailing the rationale and proposed alternative measures. The governance board will review these requests on a case-by-case basis. Decisions made by the board are final.",
        "Regular reporting is a critical component of our compliance framework. Departments are required to submit monthly status reports outlining their adherence to these guidelines. These reports will be consolidated and presented to the executive team. Any significant deviations must be accompanied by a remediation plan.",
        "Cross-functional collaboration is encouraged to achieve the objectives set forth in this document. Regular inter-departmental meetings will be held to share best practices and address common challenges. Open communication is essential for the successful execution of this policy.",
        "This policy supersedes all previous directives related to this subject matter. In the event of a conflict between this document and any prior communication, the provisions herein shall prevail. Employees should consult their supervisors if they encounter any ambiguities.",
        "The effectiveness of this policy will be evaluated annually. Feedback from employees at all levels is highly valued and will be considered during the review process. The company reserves the right to amend this document as necessary to adapt to changing circumstances."
    ]
    
    filler_content = ""
    for section_idx in range(5, 25):
        random.shuffle(filler_paragraphs)
        section_text = "\n\n".join(filler_paragraphs[:4])
        filler_content += f"\n\n{section_idx}. SUPPLEMENTARY GUIDELINES (SECTION {section_idx})\n{section_text}\nThis section provides additional context for {topic.lower()}."
        
    content = f"""
{topic.upper()}
Policy ID: {fact_3}
Effective Date: Jan 2024

1. OVERVIEW
This policy outlines the rules and regulations regarding {topic.lower()}. All employees must adhere strictly to these guidelines.

2. TIMEFRAMES AND LIMITS
Employees must complete the required process within {fact_1}. Failure to do so may result in disciplinary action.

3. APPROVAL PROCESS
All exceptions require explicit {fact_2} before any action is taken.

4. COMPLIANCE
Routine audits will be conducted. Non-compliance is subject to review by the governance board.
{filler_content}
"""
    
    qas = [
        {
            "id": f"qa_{idx:03d}_1",
            "question": f"What is the policy ID for the {topic}?",
            "is_answerable": True,
            "source_document": filename,
            "expected_answer_keywords": [fact_3],
            "type": "direct"
        },
        {
            "id": f"qa_{idx:03d}_2",
            "question": f"How long do employees have to complete the process under the {topic}?",
            "is_answerable": True,
            "source_document": filename,
            "expected_answer_keywords": [fact_1],
            "type": "direct"
        },
        {
            "id": f"qa_{idx:03d}_3",
            "question": f"Who needs to approve exceptions for {topic.lower()}?",
            "is_answerable": True,
            "source_document": filename,
            "expected_answer_keywords": [fact_2],
            "type": "direct"
        },
        {
            "id": f"qa_{idx:03d}_4",
            "question": f"Are there audits for {topic.lower()}?",
            "is_answerable": True,
            "source_document": filename,
            "expected_answer_keywords": ["Routine audits", "governance board"],
            "type": "semantic"
        },
        {
            "id": f"qa_{idx:03d}_5",
            "question": f"What is the penalty for missing a deadline on Mars under {topic}?",
            "is_answerable": False,
            "source_document": None,
            "expected_answer_keywords": [],
            "type": "unanswerable"
        }
    ]
    return content, qas

def create_pdf(filename: str, content: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    
    for line in content.split('\n'):
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        if not safe_line.strip():
            pdf.ln(8)
            continue
        wrapped = textwrap.wrap(safe_line, width=90)
        for w in wrapped:
            pdf.cell(w=200, h=8, txt=w, ln=1)
    
    filepath = DOCS_DIR / filename
    pdf.output(str(filepath))

def main():
    print("Generating Offline Deterministic Benchmark Corpus...")
    all_qa = []
    manifest_docs = []
    
    for i, topic in enumerate(TOPICS):
        print(f"[{i+1}/{len(TOPICS)}] Generating: {topic}")
        filename = f"doc_{i:03d}_{topic.replace(' ', '_').lower()[:20]}.pdf"
        
        content, qas = generate_offline_content_and_qas(topic, i, filename)
        create_pdf(filename, content)
        
        all_qa.extend(qas)
        manifest_docs.append({
            "file": filename,
            "title": topic,
            "description": f"Generated document for {topic}"
        })
        
    print(f"Generated {len(manifest_docs)} documents and {len(all_qa)} QA pairs.")
    
    with open(DATASETS_DIR / "qa_dataset.json", "w") as f:
        json.dump(all_qa, f, indent=2)
        
    manifest = {
        "dataset_version": "2.1",
        "corpus_version": "2.1",
        "documents": manifest_docs
    }
    with open(DATASETS_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("Done! Corpus is ready for bootstrapping.")

if __name__ == "__main__":
    main()
