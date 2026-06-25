import os
import re
import sys
import subprocess

def install_deps():
    print("Installing pdf generation dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2", "markdown"])
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

# Ensure dependencies are installed
try:
    from fpdf import FPDF
    import markdown
except ImportError:
    install_deps()
    from fpdf import FPDF
    import markdown

def clean_markdown_for_pdf(md_content):
    # Strip emojis and unsupported unicode characters
    # standard PDF fonts (Helvetica) only support Latin-1 (encappings up to 255)
    clean_lines = []
    for line in md_content.split('\n'):
        # Strip emojis and special characters outside latin1 range
        cleaned = "".join(c for c in line if ord(c) < 256)
        # Convert markdown links [text](url) to simple text or HTML links
        # FPDF write_html supports <a href="...">text</a>
        cleaned = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', cleaned)
        # Remove markdown image blocks
        cleaned = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', cleaned)
        # Convert code blocks to pre or code
        # FPDF HTML parser doesn't support complex CSS, but supports <font face="Courier">
        clean_lines.append(cleaned)
    return '\n'.join(clean_lines)

def build_pdf():
    print("Generating NutriTrack_Documentation.pdf...")
    
    # Read the README.md file
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print("README.md not found in the current directory.")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Clean markdown
    cleaned_md = clean_markdown_for_pdf(md_content)

    # Convert Markdown to HTML
    # We use basic extensions to keep HTML simple
    html_content = markdown.markdown(cleaned_md)

    # Clean up some tags that fpdf2 might struggle with
    # fpdf2 write_html supports <h1>, <h2>, <h3>, <h4>, <p>, <a>, <b>, <i>, <ul>, <li>, <br>
    # We replace code tags with simple Courier font tags
    html_content = html_content.replace("<code>", '<font face="Courier">')
    html_content = html_content.replace("</code>", '</font>')
    html_content = html_content.replace("<pre>", "")
    html_content = html_content.replace("</pre>", "")
    html_content = html_content.replace("<hr />", "<br/><br/>")

    # Create FPDF instance
    pdf = FPDF()
    pdf.set_margins(15, 20, 15)
    pdf.add_page()
    
    # Title Page
    pdf.set_font("helvetica", "B", 26)
    pdf.cell(0, 40, "NutriTrack", ln=True, align="C")
    pdf.set_font("helvetica", "I", 14)
    pdf.cell(0, 10, "AI-Powered Food & Nutrition Tracker", ln=True, align="C")
    pdf.cell(0, 10, "Final Project Documentation", ln=True, align="C")
    pdf.ln(20)
    pdf.line(20, 95, 190, 95)
    pdf.ln(30)
    
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 10, "Created for: Sai Phani Anirudh", ln=True, align="C")
    pdf.cell(0, 10, "Version: 3.0", ln=True, align="C")
    pdf.cell(0, 10, "Status: Deployed & Production-Ready", ln=True, align="C")
    pdf.cell(0, 10, "Date: June 2026", ln=True, align="C")
    
    # Add new page for contents
    pdf.add_page()
    pdf.set_font("helvetica", "", 10)
    
    # Parse and write simple HTML
    try:
        pdf.write_html(html_content)
    except Exception as e:
        print(f"Error rendering HTML: {e}")
        # Fallback to write plain text if HTML rendering fails
        pdf.add_page()
        pdf.set_font("helvetica", "", 10)
        pdf.write(5, cleaned_md)

    # Save PDF
    pdf.output("NutriTrack_Documentation.pdf")
    print("Successfully generated NutriTrack_Documentation.pdf!")

if __name__ == "__main__":
    build_pdf()
