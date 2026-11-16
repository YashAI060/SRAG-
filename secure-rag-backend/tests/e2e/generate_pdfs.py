import os
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

def create_handbook(output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(200, 10, txt="Acme Corp Employee Handbook 2026", ln=1, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="1. Remote Work Policy", ln=1)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt="Employees are entitled to 3 remote work days per week. Mondays and Thursdays are mandatory core days in the office. Remote work from outside the country requires VP approval and is limited to 30 days per calendar year. You must maintain a stable internet connection of at least 50Mbps down / 10Mbps up when working remotely.")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="2. Paid Time Off (PTO)", ln=1)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt="Full-time employees accrue 25 vacation days annually. Additionally, employees receive 10 sick days and 2 personal days. Up to 5 vacation days can be carried over to the next calendar year, expiring on March 31st.")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="3. Parental Leave", ln=1)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt="Primary caregivers are eligible for 16 weeks of fully paid parental leave. Secondary caregivers receive 8 weeks. To be eligible, you must have been employed continuously at Acme Corp for at least 6 months prior to the child's arrival.")
    pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="4. Hardware Refresh Cycle", ln=1)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt="Laptops are refreshed every 3 years. Engineers receive a high-performance MacBook Pro or Dell XPS. Other departments receive a standard MacBook Air or ThinkPad. Mobile phones are refreshed every 2 years with a $1000 stipend limit.")

    pdf.output(output_path)
    print(f"Created {output_path}")

def create_security_policy(output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(200, 10, txt="Information Security Policy (ISO-27001)", ln=1, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="1. Incident Reporting", ln=1)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt="Any suspected security incident must be reported within 1 hour to security@acmecorp.com or via the #security-incidents Slack channel. Do not attempt to investigate or remediate the incident yourself without authorization from the Security Operations Center (SOC).")
    pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="2. Access Control", ln=1)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt="All production access requires multi-factor authentication (MFA) via a YubiKey hardware token. SMS and Authenticator apps are no longer permitted for production systems access as of Jan 1, 2026. Access must be requested via Jira and approved by the resource owner.")
    pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="3. Data Classification", ln=1)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, txt="Public: Marketing materials.\nInternal: Employee handbook, architecture docs.\nConfidential: Customer data, financial records.\nRestricted: PII, PCI data, source code.")
    
    # Generate an image with text to test OCR
    img = Image.new('RGB', (600, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
    d.text((10,10), "SCANNED APPENDIX: VENDOR AUDIT REQUIREMENTS", fill=(0,0,0), font=font)
    d.text((10,50), "All vendors processing Restricted data must provide a valid SOC 2 Type II report.", fill=(0,0,0), font=font)
    d.text((10,90), "Vendor audits are conducted annually by the Compliance team.", fill=(0,0,0), font=font)
    img_path = "temp_scan.png"
    img.save(img_path)
    
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="Appendix A: Scanned Document", ln=1)
    pdf.image(img_path, x=10, y=30, w=180)
    
    pdf.output(output_path)
    if os.path.exists(img_path):
        os.remove(img_path)
    print(f"Created {output_path}")

def create_corrupt_pdf(output_path: str):
    with open(output_path, "wb") as f:
        f.write(b"This is not a real PDF file. It should fail parsing.")
    print(f"Created {output_path}")

def create_empty_pdf(output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.output(output_path)
    print(f"Created {output_path}")

if __name__ == "__main__":
    os.makedirs("tests/e2e/data", exist_ok=True)
    create_handbook("tests/e2e/data/handbook.pdf")
    create_security_policy("tests/e2e/data/security_policy.pdf")
    create_corrupt_pdf("tests/e2e/data/corrupt.pdf")
    create_empty_pdf("tests/e2e/data/empty.pdf")
