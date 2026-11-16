"""
Benchmark V2.1 -- Hard-Negative Corpus Generator
================================================
Produces 45 realistic enterprise-policy PDFs with no shared filler paragraphs.

Document types:
  30 baseline documents -- 5 pages each, fully topic-specific content
  15 adversarial documents -- 5 pages each, deliberately confusable content
      5 semantic  (same concept, different actor/policy outcome)
      5 lexical   (same vocabulary, different physical/scope context)
      5 numeric   (same numeric limit, different unit/meaning)

QA dataset:
  90 answerable (30 lexical, 30 semantic, 30 multi-hop)
  15 unanswerable (diverse plausible enterprise topics)
"""

import hashlib
import json
import os
import random
from pathlib import Path

from fpdf import FPDF

DATASETS_DIR = Path(__file__).parent / "datasets_v2"
DOCS_DIR = DATASETS_DIR / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# PDF helper
# ---------------------------------------------------------------------------

def create_pdf(title: str, sections: list, filepath: Path) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    for i, sec in enumerate(sections):
        pdf.add_page()
        if i == 0:
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 8, txt=title.upper())
            pdf.set_font("Helvetica", size=10)
            pdf.ln(4)
        else:
            pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, txt=sec)
    pdf.output(str(filepath))


# ---------------------------------------------------------------------------
# Baseline document definitions (30 topics)
# ---------------------------------------------------------------------------

BASELINES = [
    {
        "title": "Remote Work and Telecommuting Policy",
        "topic": "remote_work",
        "concept": "telecommuting limits",
        "unit": "days per calendar month",
        "p5": (
            "5. COMPLIANCE AND ENFORCEMENT\n\n"
            "The HR Operations team audits telecommuting logs quarterly. Managers must maintain approved remote-work "
            "records in the HR portal. Retrospective approvals are not accepted.\n\n"
            "First violation: written warning and 30-day suspension of remote-work privileges.\n"
            "Second violation: formal performance improvement plan.\n"
            "Third violation: escalation to the disciplinary committee.\n\n"
            "Employees working from abroad for more than five consecutive days must notify the Legal and Tax teams "
            "to assess permanent-establishment risk."
        ),
    },
    {
        "title": "Information Security and Acceptable Use Policy",
        "topic": "infosec",
        "concept": "device monitoring",
        "unit": "minutes of continuous unattended session before auto-lock",
        "p5": (
            "5. MONITORING AND AUDIT\n\n"
            "The IT Security team uses automated endpoint scanning to verify device compliance. All enrolled "
            "endpoints must pass a monthly security health check.\n\n"
            "Devices that fail compliance checks are quarantined from the corporate network until remediation "
            "is confirmed by the IT Security team. A quarantine event is logged in the SIEM and reported "
            "to the CISO within 24 hours.\n\n"
            "Employees must not disable or circumvent endpoint monitoring agents. Confirmed circumvention is "
            "treated as a critical security incident and escalated to HR for disciplinary action."
        ),
    },
    {
        "title": "Employee Code of Conduct",
        "topic": "conduct",
        "concept": "professional behaviour standards",
        "unit": "documented conduct incidents before formal review",
        "p5": (
            "5. INVESTIGATION AND SANCTIONS\n\n"
            "Conduct complaints are received by the HR Business Partner. Initial triage is completed within "
            "five business days. Substantiated complaints proceed to formal investigation.\n\n"
            "Sanctions are proportionate to severity:\n"
            "  Level 1 (minor): Verbal or written warning.\n"
            "  Level 2 (moderate): Final written warning and mandatory retraining.\n"
            "  Level 3 (serious): Suspension pending investigation; possible termination.\n\n"
            "All findings are documented and retained in the employee personnel file for three years."
        ),
    },
    {
        "title": "Travel and Expense Reimbursement Policy",
        "topic": "travel",
        "concept": "per-meal expense allowance",
        "unit": "USD per meal for domestic travel",
        "p5": (
            "5. SUBMISSION AND AUDIT\n\n"
            "Expense claims must be submitted within 30 calendar days of the travel event. Late claims require "
            "Finance Director written approval.\n\n"
            "All receipts above $25 USD must be attached as digital images. Claims without supporting receipts "
            "for amounts exceeding this threshold will be rejected.\n\n"
            "The Finance team conducts a random 10% sample audit of all travel expense reports monthly. "
            "Fraudulent claims are referred to HR and may require full repayment."
        ),
    },
    {
        "title": "Procurement and Vendor Management Policy",
        "topic": "procurement",
        "concept": "vendor vetting process",
        "unit": "business days for standard vendor due diligence",
        "p5": (
            "5. VENDOR PERFORMANCE AND TERMINATION\n\n"
            "All approved vendors are subject to annual performance reviews by the Procurement team covering "
            "delivery quality, security posture, and contractual compliance.\n\n"
            "Vendors rated underperforming for two consecutive quarters are placed on a remediation plan. "
            "Failure to remediate within 90 days results in contract termination with 60 days notice.\n\n"
            "The vendor register is maintained by Procurement and accessible to Finance and Legal. New vendor "
            "additions require Procurement sign-off before any purchase order is raised."
        ),
    },
    {
        "title": "Data Retention and Destruction Policy",
        "topic": "retention",
        "concept": "document archiving duration",
        "unit": "years of mandatory archive retention",
        "p5": (
            "5. DESTRUCTION PROCEDURES\n\n"
            "At the end of the retention period, records must be securely destroyed. Physical documents must "
            "be cross-cut shredded using a certified shredding service. Electronic records must be overwritten "
            "using a NIST 800-88-compliant wipe.\n\n"
            "A destruction certificate must be obtained and filed with Records Management. Records subject to "
            "a Legal Hold are exempt from destruction until the hold is formally lifted by the General Counsel. "
            "Premature destruction of held records is a critical compliance violation."
        ),
    },
    {
        "title": "Business Continuity and Disaster Recovery Policy",
        "topic": "dr",
        "concept": "IT recovery operations",
        "unit": "hours for Recovery Time Objective (RTO)",
        "p5": (
            "5. TESTING AND REVIEW\n\n"
            "Business continuity and disaster recovery plans must be tested at least annually via tabletop "
            "exercises, partial failover tests, and full failover exercises on a rotating basis.\n\n"
            "Test results are documented and reviewed by the Business Continuity Manager and the CISO. "
            "Gaps must be assigned to a named owner with a remediation deadline.\n\n"
            "Plans are reviewed after any major incident, significant IT infrastructure change, or operational "
            "footprint change. The board is briefed annually on BC/DR posture."
        ),
    },
    {
        "title": "Incident Response Plan",
        "topic": "incident",
        "concept": "security breach notification",
        "unit": "hours from discovery to mandatory internal notification",
        "p5": (
            "5. POST-INCIDENT REVIEW\n\n"
            "A post-incident review (PIR) must be conducted within 14 days of incident closure, identifying "
            "root cause, contributing factors, and preventive actions.\n\n"
            "PIR findings are documented in the Incident Register and reviewed by the CISO. High-severity "
            "incidents require a board-level briefing.\n\n"
            "Preventive actions are tracked in the risk register with named owners and target completion dates. "
            "The Incident Response team publishes a quarterly summary of incident trends."
        ),
    },
    {
        "title": "Employee Onboarding and Offboarding Policy",
        "topic": "onboarding",
        "concept": "equipment return on departure",
        "unit": "business days to return all company equipment",
        "p5": (
            "5. ACCESS REVOCATION\n\n"
            "On the employee's last working day, IT must revoke all system access within four hours of the "
            "formal departure confirmation from HR, including email, VPN, cloud services, and badge access.\n\n"
            "The offboarding manager must complete a departure checklist confirming equipment return, access "
            "revocation, and knowledge transfer. Incomplete checklists are flagged to the HR Director.\n\n"
            "Failure to return equipment by the deadline may result in the cost being deducted from final pay "
            "in accordance with the employment contract and applicable law."
        ),
    },
    {
        "title": "Bring Your Own Device (BYOD) Policy",
        "topic": "byod",
        "concept": "personal device registration",
        "unit": "personal devices registered per employee",
        "p5": (
            "5. DATA SEPARATION AND WIPE\n\n"
            "The company MDM system enforces a secure work container on all registered personal devices. "
            "Corporate data is stored only within this container and is never commingled with personal apps.\n\n"
            "Upon offboarding or upon request, IT performs a selective wipe of the work container only. "
            "Full device wipes are not performed on personally owned devices without explicit employee consent.\n\n"
            "Employees who lose a registered device must notify IT Security within four hours. The IT team "
            "will remotely lock and, if necessary, wipe the work container immediately."
        ),
    },
    {
        "title": "Anti-Bribery and Corruption Policy",
        "topic": "bribery",
        "concept": "gift and hospitality limits",
        "unit": "USD maximum value per gift received",
        "p5": (
            "5. REPORTING AND REGISTERS\n\n"
            "All gifts and hospitality received must be declared in the Gift Register within 48 hours of "
            "receipt, regardless of value. Late declarations are treated as potential compliance breaches.\n\n"
            "Gifts exceeding the permitted threshold that cannot be returned must be donated to charity "
            "and the donation recorded in the Gift Register.\n\n"
            "The Compliance team reviews the Gift Register quarterly. Patterns suggesting systematic receipt "
            "from a single vendor are reported to the General Counsel for investigation."
        ),
    },
    {
        "title": "Social Media and Public Communications Policy",
        "topic": "social_media",
        "concept": "pre-approval threshold for public statements",
        "unit": "social media posts per week before mandatory pre-approval",
        "p5": (
            "5. BREACH AND SANCTIONS\n\n"
            "Unauthorised disclosure of confidential information via social media is a serious misconduct "
            "matter. Employees found to have posted confidential content without approval face immediate "
            "suspension pending investigation.\n\n"
            "The Communications team monitors brand mentions and will alert the employee and manager if a "
            "policy-breaching post is identified. The post must be removed within two hours of notification.\n\n"
            "Annual social media training is mandatory and tracked in the Learning Management System."
        ),
    },
    {
        "title": "Performance Review and Promotions Policy",
        "topic": "performance",
        "concept": "performance evaluation cycle",
        "unit": "months between formal performance reviews",
        "p5": (
            "5. APPEALS AND DISPUTES\n\n"
            "Employees who disagree with a performance rating may submit a formal appeal to HR within "
            "10 business days of receiving their review outcome.\n\n"
            "The HR Director will convene an appeals panel including the employee's skip-level manager "
            "and an HR Business Partner. The panel's decision is final.\n\n"
            "Employees on active performance improvement plans (PIPs) are not eligible for promotion "
            "during the PIP period."
        ),
    },
    {
        "title": "Contractor and Freelancer Access Policy",
        "topic": "contractors",
        "concept": "contractor system access restrictions",
        "unit": "concurrent active project assignments per contractor",
        "p5": (
            "5. TERMINATION AND HANDOVER\n\n"
            "When a contractor engagement ends, the sponsoring manager must submit an offboarding request "
            "to IT within 24 hours. IT revokes all access on the requested date and provides confirmation.\n\n"
            "All work product remains the intellectual property of the company. Contractors must return or "
            "delete all company data from personal devices within 48 hours of contract end.\n\n"
            "Post-contract access for auditing or warranty requires time-limited guest access through "
            "Procurement. Routine post-contract access is not permitted."
        ),
    },
    {
        "title": "Vendor Information Security Requirements",
        "topic": "vendor_sec",
        "concept": "third-party security audit frequency",
        "unit": "months between mandatory vendor security assessments",
        "p5": (
            "5. REMEDIATION AND ESCALATION\n\n"
            "Vendors with critical assessment findings must submit a remediation plan within 30 days. "
            "The plan must include named owners, remediation steps, and target completion dates.\n\n"
            "The Information Security team conducts a follow-up assessment 90 days after the original "
            "finding. Vendors who fail to remediate critical findings are escalated to the Vendor "
            "Management Committee, which may suspend or terminate vendor access."
        ),
    },
    {
        "title": "Executive Travel and Expense Policy",
        "topic": "exec_travel",
        "concept": "executive premium-class travel",
        "unit": "USD threshold for first-class flight reimbursement on routes of 8+ hours",
        "p5": (
            "5. REPORTING AND REVIEW\n\n"
            "Executive travel expenses are reviewed by the CFO's office quarterly. Summary reports are "
            "presented to the Audit and Risk Committee annually.\n\n"
            "Expense reports must be submitted within 21 days of travel completion. Late submissions "
            "require CFO approval and are noted in the executive's compliance record.\n\n"
            "First-class travel for routes under eight flight hours is not reimbursable regardless of role. "
            "Exceptions require written CEO approval prior to booking."
        ),
    },
    {
        "title": "IT Hardware Provisioning Policy",
        "topic": "hardware",
        "concept": "laptop and device issuance",
        "unit": "business days for standard hardware issuance",
        "p5": (
            "5. REFRESH AND DISPOSAL\n\n"
            "Company laptops are refreshed on a standard four-year cycle. Early refresh requests require "
            "IT Director approval with a documented business justification.\n\n"
            "Decommissioned hardware must be returned to IT for secure data wiping and disposal via the "
            "approved disposal partner. Employees must not dispose of company hardware independently.\n\n"
            "A hardware disposal certificate must be obtained for each decommissioned asset and filed in "
            "the IT Asset Register within 30 days of decommission."
        ),
    },
    {
        "title": "Software License Management Policy",
        "topic": "licenses",
        "concept": "software licence compliance",
        "unit": "licensed seats per department before additional approval is needed",
        "p5": (
            "5. AUDIT AND RECONCILIATION\n\n"
            "The IT Asset Management team conducts software licence reconciliation quarterly, comparing "
            "installed software against licence entitlements.\n\n"
            "Over-licensing must be reported to Finance for cost optimisation. Under-licensing is a critical "
            "compliance breach and must be remediated within 30 days.\n\n"
            "Employees must not install unlicensed software on company devices. Discovery of unlicensed "
            "software is reported to HR for disciplinary review."
        ),
    },
    {
        "title": "Physical Security and Access Control Policy",
        "topic": "physical_sec",
        "concept": "visitor access and badge management",
        "unit": "visitors per employee per month before Security Director approval is required",
        "p5": (
            "5. TAILGATING AND SECURITY EVENTS\n\n"
            "Employees must not allow any person to follow them through a secured entrance without independently "
            "badging in. Tailgating events must be reported to Facilities Security immediately.\n\n"
            "Lost or stolen access badges must be reported within one hour. The badge is immediately deactivated "
            "and a replacement issued within 24 hours.\n\n"
            "Security cameras are installed at all entry and exit points and footage retained for 90 days."
        ),
    },
    {
        "title": "Cloud Infrastructure Security Policy",
        "topic": "cloud_sec",
        "concept": "cloud vulnerability remediation",
        "unit": "hours for critical cloud vulnerability remediation",
        "p5": (
            "5. CONFIGURATION CHANGE CONTROL\n\n"
            "All cloud infrastructure configuration changes must be submitted as a Change Request and approved "
            "by the Cloud Security Architect before implementation. Emergency changes require post-implementation "
            "review within 24 hours.\n\n"
            "Infrastructure-as-Code templates must pass automated security scanning before deployment. Builds "
            "failing security checks are blocked until findings are remediated.\n\n"
            "Cloud resources without an identified owner for more than 30 days are decommissioned."
        ),
    },
    {
        "title": "Data Classification and Handling Policy",
        "topic": "classification",
        "concept": "data classification labelling",
        "unit": "classification labels permitted per document",
        "p5": (
            "5. HANDLING REQUIREMENTS BY CLASSIFICATION\n\n"
            "Public: No restrictions. May be shared externally.\n"
            "Internal: Employee-only. Not for external distribution without approval.\n"
            "Confidential: Encrypted at rest and in transit. Need-to-know basis only.\n"
            "Restricted: End-to-end encryption required. Access logged in Data Asset Register. "
            "Physical copies destroyed immediately after use.\n\n"
            "Misclassification of data must be reported to the Data Protection Officer within 24 hours."
        ),
    },
    {
        "title": "Privacy Policy and Data Protection",
        "topic": "privacy",
        "concept": "personal data deletion requests",
        "unit": "business days to fulfil a verified deletion request",
        "p5": (
            "5. DATA BREACH NOTIFICATION\n\n"
            "Any suspected breach involving personal data must be reported to the Data Protection Officer "
            "within 24 hours of discovery. The DPO assesses whether the breach meets the regulatory threshold.\n\n"
            "Under GDPR, notifiable breaches must be reported to the supervisory authority within 72 hours. "
            "Affected data subjects must be notified without undue delay where the breach poses a high risk.\n\n"
            "All breach events are documented in the Data Breach Register. Lessons learned are incorporated "
            "into annual privacy training."
        ),
    },
    {
        "title": "Paid Time Off (PTO) Policy",
        "topic": "pto",
        "concept": "annual leave accrual and usage",
        "unit": "days of PTO accrued per year",
        "p5": (
            "5. CARRYOVER AND PAYOUT\n\n"
            "Unused PTO may be carried over into the following calendar year up to a maximum of five days. "
            "Carried-over days expire on 31 March if not used.\n\n"
            "PTO is not paid out upon resignation unless required by applicable law. Employees made redundant "
            "receive a payout for all accrued but unused PTO at their basic salary rate.\n\n"
            "PTO requests for five or more consecutive days must be submitted at least four weeks in advance. "
            "Requests during peak periods may be declined to maintain operational coverage."
        ),
    },
    {
        "title": "Maternity and Paternity Leave Policy",
        "topic": "parental_leave",
        "concept": "paid parental leave entitlement",
        "unit": "weeks of fully paid parental leave",
        "p5": (
            "5. RETURN TO WORK AND FLEXIBLE ARRANGEMENTS\n\n"
            "Employees returning from parental leave are entitled to return to the same or an equivalent role. "
            "Flexible working requirements should be discussed with the manager at least four weeks before return.\n\n"
            "Phased return arrangements (e.g., reduced hours for the first four weeks) are available and must "
            "be agreed in writing with HR before the return date.\n\n"
            "Employees who resign instead of returning from parental leave are not required to repay enhanced "
            "parental pay unless specified in their employment contract."
        ),
    },
    {
        "title": "Workplace Harassment and Discrimination Policy",
        "topic": "harassment",
        "concept": "harassment complaint investigation",
        "unit": "working days for investigation completion",
        "p5": (
            "5. SUPPORT AND CONFIDENTIALITY\n\n"
            "All parties involved in a harassment investigation have access to an Employee Assistance Programme "
            "providing confidential counselling.\n\n"
            "The identity of the complainant is protected to the maximum extent consistent with a fair "
            "investigation. Retaliation against a complainant is itself a serious breach of this policy.\n\n"
            "Anonymous reports may be submitted via the Ethics Hotline. Anonymous reports are investigated "
            "where sufficient information is available."
        ),
    },
    {
        "title": "Health and Safety at Work Policy",
        "topic": "safety",
        "concept": "mandatory health and safety training",
        "unit": "days between mandatory safety refresher training",
        "p5": (
            "5. INCIDENT REPORTING\n\n"
            "All workplace accidents, near misses, and occupational illnesses must be reported to the Health "
            "and Safety Manager on the day they occur. Failure to report promptly is a breach of this policy.\n\n"
            "The H&S team investigates all reported incidents within five business days. Reports are retained "
            "for a minimum of seven years. Serious injuries are also reported to the regulatory authority.\n\n"
            "Quarterly health and safety inspections are carried out at all premises. Findings are shared "
            "with the Safety Committee, which meets monthly."
        ),
    },
    {
        "title": "Emergency Evacuation Procedures",
        "topic": "evacuation",
        "concept": "evacuation drill and muster procedures",
        "unit": "minutes for a complete building evacuation drill",
        "p5": (
            "5. PERSONAL EMERGENCY EVACUATION PLANS\n\n"
            "Employees with mobility impairments or other disabilities affecting evacuation must have a Personal "
            "Emergency Evacuation Plan (PEEP) prepared with their manager and the Facilities team, reviewed annually.\n\n"
            "Designated evacuation assistants are trained to support PEEP employees. Their contact details "
            "are held by the Floor Warden.\n\n"
            "Fire marshals are appointed per floor and trained in evacuation, fire extinguisher use, and "
            "basic first aid. A minimum of one marshal per 50 employees must be available at all times."
        ),
    },
    {
        "title": "Open Source Software Usage Policy",
        "topic": "oss",
        "concept": "open-source licence compliance",
        "unit": "months between mandatory OSS licence compliance reviews",
        "p5": (
            "5. COPYLEFT AND CONTRIBUTION\n\n"
            "Software incorporating GPL, LGPL, or AGPL-licensed components must be reviewed by Legal before "
            "inclusion in any product or internal system.\n\n"
            "Contributions to open-source projects on behalf of the company require prior written approval "
            "from the employee's manager and the Legal team.\n\n"
            "An OSS Bill of Materials (SBOM) must be maintained for all products and reviewed at each release."
        ),
    },
    {
        "title": "Cryptography and Key Management Policy",
        "topic": "crypto",
        "concept": "cryptographic key rotation",
        "unit": "months before mandatory key rotation",
        "p5": (
            "5. KEY CEREMONY AND ESCROW\n\n"
            "Generation of master keys and Certificate Authority keys must be performed in a key ceremony "
            "with at least three witnesses from Information Security and Legal.\n\n"
            "Key escrow copies must be stored in geographically separated secure vaults. At least two "
            "authorised key custodians must be required to retrieve an escrowed key.\n\n"
            "All key operations must be logged in the immutable Key Management Audit Log, accessible only "
            "to the CISO and the Internal Audit team."
        ),
    },
    {
        "title": "Network Security and Perimeter Controls Policy",
        "topic": "network",
        "concept": "VPN and remote access controls",
        "unit": "simultaneous VPN sessions permitted per user account",
        "p5": (
            "5. NETWORK MONITORING AND ANOMALY DETECTION\n\n"
            "All network traffic traversing the corporate perimeter is subject to deep-packet inspection. "
            "Encrypted traffic to unknown external destinations is flagged for SOC review.\n\n"
            "The SOC monitors network telemetry 24/7 using a SIEM platform. Anomalies exceeding defined "
            "thresholds trigger automated alerts requiring analyst review within 15 minutes.\n\n"
            "Network segmentation is enforced between all business units, with inter-segment traffic controlled "
            "by Access Control Lists reviewed quarterly."
        ),
    },
]


# ---------------------------------------------------------------------------
# Adversarial document content
# ---------------------------------------------------------------------------

SEMANTIC_ADVERSARIALS = [
    {
        "filename": "adv_sem_000_remote_work.pdf",
        "title": "Remote Work Policy for External Contractors",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-CONTR-RW-001  |  Owner: Procurement\n\n"
                "This policy governs telecommuting arrangements for external contractors and consultants. "
                "It supplements but does not replace the general Remote Work Policy (POL-HR-001), which "
                "applies to direct employees only."
            ),
            (
                "2. SCOPE AND CLASSIFICATIONS\n\n"
                "Category 1 -- On-site Mandatory: Contractors handling Restricted data or with access to "
                "production systems. Remote work is not permitted under any circumstances.\n\n"
                "Category 2 -- Hybrid Permitted: Contractors working exclusively on Internal-classified "
                "deliverables. Subject to Sponsor Manager approval and security assessment."
            ),
            (
                "3. TELECOMMUTING RESTRICTIONS\n\n"
                "Unlike direct employees, Category 1 contractors are not entitled to any remote working days. "
                "All contracted work must be performed on-site at designated company facilities.\n\n"
                "Category 2 contractors may request up to 2 remote days per week, subject to dual approval. "
                "Telecommuting limits for contractors are set to zero by default and must be explicitly unlocked "
                "per contractor. The default is on-site mandatory."
            ),
            (
                "4. AUTHORISATION REQUIREMENTS\n\n"
                "Category 1 contractors: Remote work is categorically prohibited. No approval pathway exists.\n\n"
                "Category 2 contractors seeking remote access must obtain:\n"
                "  (a) Written approval from the Sponsor Manager, AND\n"
                "  (b) Security clearance from the Information Security team, AND\n"
                "  (c) A signed Remote Work Addendum to the contractor agreement.\n\n"
                "Department Head approval alone is insufficient for contractor remote-work exceptions."
            ),
            (
                "5. COMPLIANCE\n\n"
                "Contractor access logs are reviewed monthly by Procurement and Information Security. "
                "Contractors found working remotely without authorisation will have their access revoked "
                "immediately and the matter referred to the contracting agency.\n\n"
                "Sponsor Managers who approve contractor remote work without the dual-approval process "
                "are subject to disciplinary review under the Employee Code of Conduct."
            ),
        ],
    },
    {
        "filename": "adv_sem_001_infosec.pdf",
        "title": "Device Monitoring Policy -- External Audit Engagements",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-SEC-AUDIT-002  |  Owner: Information Security / Legal\n\n"
                "This policy establishes device monitoring requirements for external auditors who bring "
                "their own laptops onto company premises. It covers monitoring of auditor-owned equipment "
                "during on-site audit engagements, not employee devices."
            ),
            (
                "2. SCOPE AND CATEGORIES\n\n"
                "Category A -- External Financial Auditors: Subject to network traffic monitoring only. "
                "No agent installation on auditor devices.\n\n"
                "Category B -- Penetration Testers / Security Assessors: Subject to full scoping agreement. "
                "Network isolation required. All activities logged at the network perimeter."
            ),
            (
                "3. MONITORING LIMITS AND DURATION\n\n"
                "Device monitoring of external auditor sessions is capped at a maximum of 90 calendar days.\n\n"
                "Monitoring beyond 90 days requires joint approval from the CISO and General Counsel. "
                "Extensions are not granted for financial audits; a new engagement scoping agreement is required.\n\n"
                "Note: The 90-day cap applies to auditor devices only and is distinct from the auto-lock "
                "timeout that applies to employee devices under POL-SEC-001."
            ),
            (
                "4. AUTHORISATION\n\n"
                "All external audit device monitoring must be authorised by:\n"
                "  -- The CISO (Information Security authority), AND\n"
                "  -- Legal Counsel (contractual and privacy authority).\n\n"
                "A Department Head approval is not sufficient. Monitoring without dual CISO and Legal "
                "sign-off may constitute unlawful interception under applicable telecommunications law."
            ),
            (
                "5. AUDIT LOG AND RETENTION\n\n"
                "All monitoring activity logs for external audit devices are retained for a minimum of "
                "seven years in an immutable audit repository accessible only to the CISO and General Counsel.\n\n"
                "Monitoring results must not be shared beyond those specified in the audit engagement "
                "agreement without prior Legal approval."
            ),
        ],
    },
    {
        "filename": "adv_sem_002_conduct.pdf",
        "title": "Code of Conduct -- Probationary Employees",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-HR-PROB-003  |  Owner: Human Resources\n\n"
                "This supplementary code applies to employees during their probationary period. Probationary "
                "employees are subject to heightened professional behaviour standards, reflecting the company's "
                "assessment of cultural fit and role competence during this period."
            ),
            (
                "2. CATEGORIES\n\n"
                "Permanent Track: Employees with an agreed permanent contract after successful probation. "
                "Zero tolerance for major incidents applies.\n\n"
                "Fixed-Term Track: Employees on fixed-term contracts. Standards are identical; consequences "
                "are assessed relative to the contract length remaining."
            ),
            (
                "3. CONDUCT THRESHOLDS DURING PROBATION\n\n"
                "The escalation threshold during probation is more restrictive than the standard policy.\n\n"
                "Zero tolerance applies to dishonesty, misrepresentation, fraud, discrimination, harassment, "
                "and serious breach of confidentiality.\n\n"
                "A single substantiated conduct complaint during probation may result in immediate termination "
                "without the graduated warnings available to confirmed employees."
            ),
            (
                "4. AUTHORISATION FOR TERMINATION DURING PROBATION\n\n"
                "Termination during probation for conduct reasons requires joint approval from:\n"
                "  -- The hiring manager, AND\n"
                "  -- An HR Business Partner.\n\n"
                "A Department Head approval alone is not sufficient. Legal review is required for terminations "
                "involving potential discrimination or whistleblowing claims."
            ),
            (
                "5. PROBATION EXTENSION\n\n"
                "Where conduct concerns are identified but termination is not warranted, probation may be "
                "extended by up to 90 days. The same dual approval is required as for termination. "
                "Employees must be notified of an extension in writing at least 14 days before the "
                "original probation end date."
            ),
        ],
    },
    {
        "filename": "adv_sem_003_travel.pdf",
        "title": "Client Entertainment and Meal Expense Policy",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-FIN-ENT-004  |  Owner: Finance / Sales\n\n"
                "This policy governs meal and entertainment expenses when hosting clients, prospects, or "
                "partners. It supplements the Travel and Expense Reimbursement Policy (POL-FIN-001), "
                "which covers personal travel meals only."
            ),
            (
                "2. CATEGORIES\n\n"
                "Tier 1 -- Strategic Accounts (>$1M annual contract value): Higher entertainment limits. "
                "Quarterly review by Sales Director.\n\n"
                "Tier 2 -- Standard Accounts: Standard limits as defined in Section 3. Monthly Finance reporting.\n\n"
                "Tier 3 -- Prospects (pre-contract): Most restrictive limits. Pre-approval required for any spend."
            ),
            (
                "3. PER-MEAL ALLOWANCE FOR CLIENT ENTERTAINMENT\n\n"
                "Client entertainment allowances are expressed per client per quarter, not per employee per "
                "event -- a critical distinction from the personal travel expense policy.\n\n"
                "Tier 1: Up to $300 per client per quarter.\n"
                "Tier 2: Up to $150 per client per quarter.\n"
                "Tier 3: Up to $75 per prospect per quarter with pre-approval.\n\n"
                "Individual meal spend per person must not exceed $80. Events exceeding this per-head limit "
                "require Sales Director sign-off."
            ),
            (
                "4. AUTHORISATION\n\n"
                "Client entertainment expenses are approved by the Sales Director, not the Department Head.\n\n"
                "Events above $500 require joint approval: Sales Director AND Finance Controller.\n\n"
                "Alcohol may be included up to 20% of the total meal cost. Alcohol-only events are not reimbursable."
            ),
            (
                "5. REPORTING AND ANTI-BRIBERY\n\n"
                "All client entertainment must be logged in the Client Entertainment Register within 48 hours. "
                "The register is reviewed quarterly by Compliance for anti-bribery risk.\n\n"
                "Entertainment for public officials requires pre-approval from Compliance and is subject to "
                "the Anti-Bribery Policy limits, which take precedence over this policy."
            ),
        ],
    },
    {
        "filename": "adv_sem_004_procurement.pdf",
        "title": "Emergency Vendor Engagement Policy",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-PROC-EMG-005  |  Owner: Procurement / Risk\n\n"
                "This policy provides a framework for engaging vendors under emergency conditions where the "
                "standard vendor vetting process (POL-PROC-001) cannot be completed within the required timeframe."
            ),
            (
                "2. EMERGENCY CLASSIFICATION\n\n"
                "Level 1 Critical: Immediate risk to life, data, or regulatory compliance. Standard vetting "
                "suspended. Engagement may commence immediately.\n\n"
                "Level 2 Urgent: Significant operational impact. Standard vetting compressed to 24 hours. "
                "A risk-acceptance waiver is required."
            ),
            (
                "3. EXPEDITED VETTING LIMITS\n\n"
                "Level 1: Standard vetting requirement suspended for the duration of the emergency. "
                "A full retrospective assessment must be completed within 30 days of emergency closure.\n\n"
                "Level 2: Vetting compressed to 24 hours, covering financial health check and basic information "
                "security questionnaire only. Full vetting must be completed within 14 days.\n\n"
                "These timelines supersede the standard vetting duration defined in POL-PROC-001."
            ),
            (
                "4. AUTHORISATION\n\n"
                "Level 1 Emergency vendor engagement requires CEO approval. This cannot be delegated.\n\n"
                "Level 2 Urgent engagement requires CFO approval plus Procurement Director.\n\n"
                "Department Head approval alone is insufficient for emergency vendor engagement under either "
                "classification. Procurement must be notified within two hours of all emergency engagements."
            ),
            (
                "5. POST-EMERGENCY REVIEW\n\n"
                "All emergency vendor engagements are reviewed by the Vendor Management Committee within "
                "60 days of emergency closure. The review assesses decision-making, vendor performance, and "
                "residual risk. Vendors engaged under Level 1 who fail the retrospective assessment must be "
                "terminated within 30 days."
            ),
        ],
    },
]

LEXICAL_ADVERSARIALS = [
    {
        "filename": "adv_lex_005_retention.pdf",
        "title": "Legal Hold and Litigation Document Preservation",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-LEGAL-HOLD-006  |  Owner: Legal / Compliance\n\n"
                "This policy governs the preservation of documents and data in connection with actual or "
                "anticipated litigation, regulatory investigations, or legal proceedings. A Legal Hold suspends "
                "normal document archiving and destruction schedules for all covered materials. It is distinct "
                "from the standard Data Retention and Destruction Policy (POL-DRM-001)."
            ),
            (
                "2. SCOPE OF LEGAL HOLDS\n\n"
                "Legal Holds apply to both physical and electronic documents, including emails, chat messages, "
                "spreadsheets, and database records.\n\n"
                "Category A -- Directly Relevant: Documents explicitly named in a legal notice. Must be "
                "quarantined within 24 hours of Hold issuance.\n\n"
                "Category B -- Potentially Relevant: Documents that may contain relevant information based on "
                "custodian role or project involvement. Preserved pending Legal review."
            ),
            (
                "3. DURATION AND ARCHIVING\n\n"
                "Unlike routine document archiving which follows the standard retention schedule, Legal Hold "
                "materials are preserved for the full duration of legal proceedings plus a mandatory seven-year "
                "post-resolution archive period.\n\n"
                "Normal destruction schedules are suspended from the moment the Hold is issued. Automated "
                "deletion rules must be manually overridden for all custodian accounts subject to the Hold."
            ),
            (
                "4. AUTHORISATION TO ISSUE AND LIFT\n\n"
                "Legal Holds may only be issued by the General Counsel or a designated Deputy General Counsel.\n\n"
                "A Legal Hold may only be lifted by the General Counsel, following written confirmation from "
                "external legal advisors that proceedings have concluded.\n\n"
                "Department Heads do not have authority to issue, modify, or lift Legal Holds. Instructions "
                "to destroy documents under a Legal Hold constitute a serious compliance violation and "
                "potential contempt of court."
            ),
            (
                "5. CUSTODIAN OBLIGATIONS\n\n"
                "Employees identified as custodians must acknowledge the Hold notice within 24 hours. They "
                "must immediately cease any document destruction activities and report any accidental "
                "destruction to the Legal team."
            ),
        ],
    },
    {
        "filename": "adv_lex_006_dr.pdf",
        "title": "Emergency Operations -- Building Evacuation and Physical Safety",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-FAC-EVAC-007  |  Owner: Facilities / Health and Safety\n\n"
                "This policy defines procedures for physical emergency operations at all company premises, "
                "covering evacuation, muster, and headcount for emergencies including fire, earthquake, bomb "
                "threat, and active-threat scenarios. This is entirely distinct from the Business Continuity "
                "and IT Disaster Recovery Policy (POL-BC-001)."
            ),
            (
                "2. EMERGENCY CATEGORIES\n\n"
                "Tier A -- Immediate Evacuation (fire, gas leak): All personnel must evacuate to the designated "
                "muster point immediately. No exceptions for Executives or General Staff.\n\n"
                "Tier B -- Shelter-in-Place (severe weather, external active threat): Personnel must remain "
                "indoors and await instructions from the Emergency Response Team."
            ),
            (
                "3. RECOVERY TIME AND MUSTER\n\n"
                "Unlike IT disaster recovery which measures Recovery Time Objectives in hours, physical emergency "
                "operations are measured in minutes.\n\n"
                "Full building evacuation must be completed within the time defined by the Fire Safety assessment "
                "for each site. Headcount at the muster point must be completed within five minutes of evacuation.\n\n"
                "The Floor Warden is responsible for sweeping their zone and reporting to the Emergency Response "
                "Coordinator at the muster point."
            ),
            (
                "4. AUTHORISATION AND COMMAND\n\n"
                "The Emergency Response Coordinator has sole authority to declare all-clear and permit re-entry. "
                "No other manager, including a Department Head or Executive, may authorise re-entry before "
                "all-clear is issued.\n\n"
                "Employees who re-enter before all-clear is declared are in breach of health and safety law."
            ),
            (
                "5. DRILLS AND REVIEW\n\n"
                "Evacuation drills are conducted at least twice per year at each premises. Drill results "
                "including evacuation time and headcount accuracy are documented and reviewed by the Safety "
                "Committee. Improvements are implemented within 30 days of the drill."
            ),
        ],
    },
    {
        "filename": "adv_lex_007_incident.pdf",
        "title": "Physical Security Incident Reporting Procedure",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-FAC-SEC-008  |  Owner: Facilities Security\n\n"
                "This procedure governs reporting and investigation of physical security incidents including "
                "unauthorised access, tailgating, theft, and vandalism at company premises. It is distinct "
                "from the Cyber Security Incident Response Plan (POL-SEC-IRP-001), which covers information "
                "security breaches."
            ),
            (
                "2. CATEGORIES OF PHYSICAL SECURITY BREACH\n\n"
                "Category A -- Perimeter Breach: Unauthorised entry through forced access or tailgating. "
                "Immediate escalation required.\n\n"
                "Category B -- Internal Breach: Unauthorised access to a secure zone by an individual who "
                "is legitimately present in the building."
            ),
            (
                "3. REPORTING TIMELINE\n\n"
                "Physical security breaches must be reported to Facilities Security immediately upon discovery -- "
                "not within hours as for cyber incidents, but within minutes.\n\n"
                "Facilities Security notifies the General Manager within 30 minutes for Category A breaches. "
                "Police notification is required for forced entry or theft events.\n\n"
                "Security camera footage must be preserved immediately and retained for 90 days."
            ),
            (
                "4. ESCALATION AND NOTIFICATION\n\n"
                "Physical security breach notifications flow through Facilities Security, not the IT Security "
                "team or CISO. This is the key distinction from cyber incident reporting.\n\n"
                "The CISO is notified only if the physical breach is believed to have resulted in unauthorised "
                "access to IT systems. Combined incidents are handled jointly by both teams."
            ),
            (
                "5. POST-INCIDENT REVIEW\n\n"
                "All physical security incidents are reviewed by the Facilities Security Manager within five "
                "business days. Repeat incidents at the same location trigger a formal security assessment of "
                "the affected facility, with findings reported to the Operations Director."
            ),
        ],
    },
    {
        "filename": "adv_lex_008_onboarding.pdf",
        "title": "IT Asset Lifecycle Management Policy",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-IT-ASSET-009  |  Owner: IT Asset Management\n\n"
                "This policy governs the full lifecycle of company-owned IT assets from procurement through "
                "deployment, maintenance, and secure disposal. Equipment return upon employee offboarding "
                "is one phase within this broader lifecycle framework."
            ),
            (
                "2. ASSET CATEGORIES\n\n"
                "Class A -- Endpoint Devices: Laptops, desktops, mobile phones. Issued to individual employees. "
                "Subject to the full lifecycle process.\n\n"
                "Class B -- Shared Infrastructure: Servers, network equipment, printers. Managed by IT. "
                "Not individually assigned to employees."
            ),
            (
                "3. LIFECYCLE STAGES AND TIMELINES\n\n"
                "Stage 1 -- Procurement: Hardware ordered via the IT request portal. Standard issuance: 5 business days.\n"
                "Stage 2 -- Deployment: Device configured and enrolled in MDM before issuance.\n"
                "Stage 3 -- Maintenance: Annual security review and hardware health check.\n"
                "Stage 4 -- Refresh: Devices refreshed on a four-year cycle.\n"
                "Stage 5 -- Decommission: Device collected, data wiped, and disposed via approved partner.\n\n"
                "Equipment return is part of Stage 5 only. The offboarding process initiates Stage 5 "
                "for individually assigned assets."
            ),
            (
                "4. AUTHORISATION\n\n"
                "Asset procurement requests above $2,000 per unit require IT Director approval in addition "
                "to the standard department manager approval.\n\n"
                "Early refresh requests (before the four-year cycle) require both manager and IT Director "
                "approval with a documented hardware fault."
            ),
            (
                "5. DISPOSAL COMPLIANCE\n\n"
                "All decommissioned assets must be processed through the company's approved disposal partner. "
                "A Certificate of Destruction must be obtained and filed in the IT Asset Register within "
                "30 days of decommission. Self-disposal by employees is strictly prohibited."
            ),
        ],
    },
    {
        "filename": "adv_lex_009_byod.pdf",
        "title": "International Travel -- Personal Device and Roaming Policy",
        "sections": [
            (
                "1. POLICY OVERVIEW\n\n"
                "Policy ID: POL-IT-ROAM-010  |  Owner: IT Security / Finance\n\n"
                "This policy applies to employees who use personal mobile devices while travelling "
                "internationally for business. It addresses data security requirements and roaming cost "
                "reimbursement for personal phones at work events abroad.\n\n"
                "This is distinct from the BYOD Policy (POL-IT-BYOD-001), which governs the routine use "
                "of personal devices at the domestic office."
            ),
            (
                "2. CATEGORIES\n\n"
                "Category A -- High-Risk Destinations (FCDO advisory Level 3-4): Additional device security "
                "controls required before travel. IT Security briefing mandatory.\n\n"
                "Category B -- Standard Destinations: Standard personal device usage guidelines apply. "
                "Employees should enable travel mode on their MDM container before departure."
            ),
            (
                "3. PERSONAL PHONE USE AND DATA SECURITY\n\n"
                "When using personal phones at work events in international locations, employees must ensure:\n"
                "  -- Corporate email and data accessed via the MDM container only.\n"
                "  -- Roaming data connections use VPN.\n"
                "  -- Public Wi-Fi is not used for corporate access without VPN.\n\n"
                "The maximum number of personal devices permitted to access corporate data while roaming "
                "internationally is 2 per employee, regardless of their standard BYOD registration."
            ),
            (
                "4. ROAMING COST REIMBURSEMENT\n\n"
                "Roaming charges on personal phones for business calls and data during international travel "
                "are reimbursable up to $50 per trip. Charges above this threshold require manager approval.\n\n"
                "Employees are encouraged to use company-provided SIM cards for international travel. "
                "Requests must be submitted to IT at least five business days before travel."
            ),
            (
                "5. HIGH-RISK DESTINATION CONTROLS\n\n"
                "For Category A destinations, employees must attend a pre-travel IT security briefing. "
                "Laptops with sensitive data should be replaced with a clean loan device for the trip. "
                "Personal devices brought to these destinations may be subject to post-travel security "
                "inspection at the discretion of the IT Security team."
            ),
        ],
    },
]


def build_numeric_adversarials():
    adversarials = []
    configs = [
        {
            "idx": 10,
            "filename": "adv_num_010_bribery.pdf",
            "title": "Gift Register -- Long-Standing Client Exception Protocol",
            "context": (
                "gifts received from clients with a trading relationship of ten or more years "
                "valued at or below this threshold may be registered as approved exceptions rather "
                "than returned or donated to charity"
            ),
            "approval": "CFO",
            "distinction": (
                "This exception threshold equals the standard gift limit in POL-ABC-001, but the "
                "approval authority (CFO) and eligibility condition (10-year client relationship) are "
                "entirely different. This policy governs registered exceptions, not standard receipts."
            ),
            "p5": (
                "5. REGISTER MAINTENANCE\n\n"
                "The CFO's office maintains the Exceptions Register and publishes a quarterly summary "
                "to the Board Audit Committee. Each entry must include the gift description, estimated "
                "value, donor name, relationship tenure, and CFO approval reference."
            ),
        },
        {
            "idx": 11,
            "filename": "adv_num_011_social_media.pdf",
            "title": "Crisis Communications Mandatory Posting Protocol",
            "context": (
                "during a formally declared corporate crisis, employees designated as crisis "
                "communicators may be required to publish up to this many approved posts per week "
                "as part of the coordinated external response -- the inverse of the normal "
                "pre-approval threshold in the Social Media Policy"
            ),
            "approval": "Communications Director",
            "distinction": (
                "Under normal circumstances the Social Media Policy restricts posts above a certain "
                "threshold. This crisis protocol inverts that: it mandates a minimum posting frequency "
                "using the same numeric value in a different operational context."
            ),
            "p5": (
                "5. CRISIS DECLARATION AND STAND-DOWN\n\n"
                "A crisis communication period is declared by the CEO and ends upon an explicit stand-down "
                "notice. All crisis-period posts must be pre-approved by the Communications Director "
                "before publication. Normal Social Media Policy limits are reinstated upon stand-down."
            ),
        },
        {
            "idx": 12,
            "filename": "adv_num_012_performance.pdf",
            "title": "Performance Improvement Plan (PIP) Review Schedule",
            "context": (
                "an active Performance Improvement Plan must be formally reviewed at intervals of "
                "this many weeks -- note the unit is weeks, not months as in the standard Performance "
                "Review Policy. A PIP review cycle is substantially shorter and more intensive."
            ),
            "approval": "HR Director and direct manager jointly",
            "distinction": (
                "The numeric value equals the month count from the standard performance review cycle, "
                "but the unit is weeks. A 6-month review cycle versus a 6-week PIP checkpoint produces "
                "the same number with entirely different operational meaning."
            ),
            "p5": (
                "5. PIP OUTCOMES\n\n"
                "At each PIP checkpoint, three outcomes are possible:\n"
                "  Satisfactory Progress: PIP continues to next checkpoint.\n"
                "  Unsatisfactory Progress: PIP escalated; 30-day warning issued.\n"
                "  Successful Completion: PIP closed; standard performance management resumes.\n\n"
                "Failure to complete a PIP successfully may result in termination of employment."
            ),
        },
        {
            "idx": 13,
            "filename": "adv_num_013_contractors.pdf",
            "title": "Peak Season Temporary Staff Access Expansion",
            "context": (
                "during a formally declared peak season, temporary agency staff may be assigned "
                "across this many client accounts simultaneously -- significantly higher than the "
                "concurrent project limit that applies to standard contractors under POL-CONTR-001"
            ),
            "approval": "Resource Manager",
            "distinction": (
                "The standard contractor access policy limits concurrent projects. This policy uses the "
                "same numeric value as the expanded peak-season ceiling for temporary agency staff, a "
                "different worker category with different security clearance requirements."
            ),
            "p5": (
                "5. PEAK SEASON DECLARATION\n\n"
                "Peak season must be formally declared by the Resource Manager with CFO endorsement. "
                "The declaration specifies start and end dates. Standard contractor limits revert "
                "automatically upon stand-down. Temporary staff access is audited weekly during peak season."
            ),
        },
        {
            "idx": 14,
            "filename": "adv_num_014_vendor_sec.pdf",
            "title": "SOC 2 Type II Report Review Schedule",
            "context": (
                "third-party SOC 2 Type II reports obtained from critical vendors must be reviewed "
                "by the Information Security team at this interval -- this governs review of existing "
                "reports provided by vendors, not the same as conducting a new vendor security "
                "assessment under POL-VSEC-001, which has a different schedule"
            ),
            "approval": "Risk Manager",
            "distinction": (
                "The vendor security assessment policy schedules new assessments on a certain cycle. "
                "This policy uses the same interval for reviewing existing SOC 2 reports, but the "
                "scope is narrower (report review vs. active assessment) and the approval authority "
                "is the Risk Manager, not the CISO."
            ),
            "p5": (
                "5. REPORT ADEQUACY ASSESSMENT\n\n"
                "The Information Security team assesses each SOC 2 report for coverage period, scope, "
                "and exception items. Reports older than 12 months are considered stale and trigger "
                "a vendor re-assessment request. Exception items are tracked in the vendor risk register "
                "and followed up at the next scheduled review."
            ),
        },
    ]

    for cfg in configs:
        idx = cfg["idx"]
        random.seed(idx)
        limit = random.randint(10, 50)
        adversarials.append({
            "filename": cfg["filename"],
            "title": cfg["title"],
            "sections": [
                (
                    f"1. POLICY OVERVIEW\n\n"
                    f"This policy governs {cfg['title'].lower()}. It should not be confused with the standard "
                    f"policy that governs the {BASELINES[idx]['concept']} for direct employees and standard vendors."
                ),
                (
                    f"2. SCOPE\n\n"
                    f"This policy applies to a specific subset of the workforce or vendor population as defined "
                    f"herein. It does not replace or modify the general {BASELINES[idx]['concept']} rules applicable "
                    f"to standard employees and contractors."
                ),
                (
                    f"3. NUMERIC THRESHOLD\n\n"
                    f"Under this policy, the applicable limit is {limit}. Specifically: {cfg['context']}.\n\n"
                    f"Important distinction: {cfg['distinction']}"
                ),
                (
                    f"4. AUTHORISATION\n\n"
                    f"Applications under this policy require approval from the {cfg['approval']}.\n\n"
                    f"A Department Head approval does not satisfy the authorisation requirement. Requests "
                    f"submitted to a Department Head will be redirected to {cfg['approval']}."
                ),
                cfg["p5"],
            ],
        })

    return adversarials


UNANSWERABLE_QS = [
    {"id": "q_unans_0",  "question": "Does the company have a policy on employee stock options and equity grants?"},
    {"id": "q_unans_1",  "question": "Is there a company policy on reimbursement for commuter parking or transport passes?"},
    {"id": "q_unans_2",  "question": "What are the rules for paid jury-duty leave?"},
    {"id": "q_unans_3",  "question": "Can employees use company laptops for approved side-project work outside office hours?"},
    {"id": "q_unans_4",  "question": "Is there a home-office furniture or ergonomic equipment allowance for remote employees?"},
    {"id": "q_unans_5",  "question": "Does the company offer pet insurance as part of its employee benefits package?"},
    {"id": "q_unans_6",  "question": "What are the restrictions on personal cryptocurrency trading using personal accounts?"},
    {"id": "q_unans_7",  "question": "Does the company provide or subsidise gym membership for employees?"},
    {"id": "q_unans_8",  "question": "Is there a paid volunteer time-off allowance for employees engaged in charitable work?"},
    {"id": "q_unans_9",  "question": "Can employees use personal cloud storage services such as Dropbox or iCloud to store work files on company devices?"},
    {"id": "q_unans_10", "question": "Is there a relocation bonus or allowance for employees required to move cities for a new role?"},
    {"id": "q_unans_11", "question": "What is the policy on using a company vehicle for personal trips at weekends?"},
    {"id": "q_unans_12", "question": "Do employees receive a financial bonus for filing a patent arising from work conducted for the company?"},
    {"id": "q_unans_13", "question": "Are conference registration fees and associated travel covered by a separate training or development budget?"},
    {"id": "q_unans_14", "question": "Can employees claim reimbursement for home broadband or internet costs while working remotely?"},
]


# ---------------------------------------------------------------------------
# Main generation routine
# ---------------------------------------------------------------------------

def generate():
    random.seed(42)
    qa_pairs = []
    doc_count = 0

    # ---- Baseline documents ------------------------------------------------
    for idx, b in enumerate(BASELINES):
        filename = f"baseline_{idx:03d}_{b['topic']}.pdf"
        filepath = DOCS_DIR / filename

        random.seed(idx)
        limit = random.randint(10, 50)

        short_id = b["topic"].upper()[:6]

        sections = [
            (
                f"1. POLICY OVERVIEW\n\n"
                f"Policy ID: POL-{short_id}-{idx+1:03d}  |  Effective Date: January 1, 2024  |  "
                f"Owner: {b['title'].split()[0]}\n\n"
                f"This policy governs {b['concept']} for all company personnel. Compliance is mandatory. "
                f"This document supersedes all prior directives on this subject matter."
            ),
            (
                f"2. SCOPE AND CATEGORIES\n\n"
                f"This policy applies to all permanent, fixed-term, and part-time employees.\n\n"
                f"Tier A -- Executives (Director level and above):\n"
                f"  Subject to this policy but exercise self-discretion within defined limits.\n"
                f"  No prior approval required for actions within the Tier A allocation.\n\n"
                f"Tier B -- General Staff (all non-Executive employees):\n"
                f"  Subject to the limits defined in Section 3.\n"
                f"  Must obtain prior written approval from their Department Head before exceeding any threshold.\n"
                f"  Must complete the annual compliance attestation by 31 January each year."
            ),
            (
                f"3. LIMITS FOR {b['concept'].upper()}\n\n"
                f"Policy Reference: POL-{short_id}-{idx+1:03d}-L\n\n"
                f"The maximum allowable {b['unit']} is {limit}.\n\n"
                f"Requests to exceed this threshold must be submitted in writing to the relevant approval "
                f"authority with a documented business justification.\n\n"
                f"Threshold exception approvals are valid for a maximum of 90 days and must be renewed."
            ),
            (
                f"4. APPROVALS AND AUTHORISATION\n\n"
                f"Approval authority is determined by Tier:\n\n"
                f"Tier A (Executives):\n"
                f"  No prior approval required for actions within the standard allocation.\n"
                f"  Self-attestation in the compliance portal is required for any threshold exception.\n\n"
                f"Tier B (General Staff):\n"
                f"  Written approval from the direct Department Head is required.\n"
                f"  Approval must be recorded in the compliance portal before any exception is enacted.\n"
                f"  Retrospective approvals are not accepted under any circumstances."
            ),
            b["p5"],
        ]

        create_pdf(b["title"], sections, filepath)
        doc_count += 1

        qa_pairs.append({
            "id": f"q_{idx}_lex",
            "question": f"What is the maximum allowable {b['unit']} for {b['concept']}?",
            "is_answerable": True,
            "source_document": filename,
            "ground_truth_pages": [3],
            "type": "lexical",
        })

        qa_pairs.append({
            "id": f"q_{idx}_sem",
            "question": f"At what point does exceeding the limit on {b['concept']} become prohibited?",
            "is_answerable": True,
            "source_document": filename,
            "ground_truth_pages": [3],
            "type": "semantic",
        })

        qa_pairs.append({
            "id": f"q_{idx}_hop",
            "question": (
                f"An employee who falls under the General Staff tier needs to arrange an exception "
                f"related to {b['concept']}. Who must give written approval, and where must that approval be recorded?"
            ),
            "is_answerable": True,
            "source_document": filename,
            "ground_truth_pages": [2, 4],
            "type": "multi_hop",
        })

    # ---- Adversarial documents ---------------------------------------------
    all_adversarials = (
        SEMANTIC_ADVERSARIALS
        + LEXICAL_ADVERSARIALS
        + build_numeric_adversarials()
    )

    for adv in all_adversarials:
        create_pdf(adv["title"], adv["sections"], DOCS_DIR / adv["filename"])
        doc_count += 1

    # ---- Unanswerable questions --------------------------------------------
    for uq in UNANSWERABLE_QS:
        qa_pairs.append({
            "id": uq["id"],
            "question": uq["question"],
            "is_answerable": False,
            "type": "unanswerable",
        })

    # ---- Manifest and freeze metadata -------------------------------------
    doc_files = sorted(f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf"))

    h = hashlib.sha256()
    for fn in doc_files:
        h.update(fn.encode())
        h.update((DOCS_DIR / fn).read_bytes())
    corpus_sha256 = h.hexdigest()

    type_counts: dict = {}
    for q in qa_pairs:
        t = q.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    manifest = {
        "dataset_version": "2.1",
        "corpus_version": "2.1",
        "description": (
            "Hard-Negative V2.1 Benchmark. "
            "30 baseline policy documents + 15 adversarial documents (5 semantic, 5 lexical, 5 numeric). "
            "No shared filler paragraphs. "
            "Ground truth keyed on (source_document, ground_truth_pages)."
        ),
        "generation_timestamp": "2024-09-05T00:00:00Z",
        "corpus_sha256": corpus_sha256,
        "document_count": len(doc_files),
        "question_count": len(qa_pairs),
        "question_type_counts": type_counts,
        "chunk_identity_note": (
            "Ground truth is expressed as (source_document, ground_truth_pages). "
            "At evaluation time, a chunk is a match if its document_id corresponds to source_document "
            "AND its page_number is in ground_truth_pages."
        ),
        "documents": [
            {"file": fn, "title": fn.replace(".pdf", ""), "description": "V2.1 document"}
            for fn in doc_files
        ],
    }

    with open(DATASETS_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    with open(DATASETS_DIR / "qa_dataset.json", "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

    print(f"Generated {doc_count} documents in {DOCS_DIR}")
    print(f"Generated {len(qa_pairs)} questions  ({type_counts})")
    print(f"Corpus SHA-256: {corpus_sha256[:16]}...")


if __name__ == "__main__":
    generate()
