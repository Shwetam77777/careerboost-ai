import fitz  # PyMuPDF
import docx
import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.colors import HexColor
import re
import io
import zipfile
import datetime
from typing import Dict, List


# ─────────────────────────────────────────────
# FILE PARSING
# ─────────────────────────────────────────────

def parse_pdf(file) -> str:
    try:
        pdf_bytes = file.read() if hasattr(file, 'read') else file
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        raise Exception(f"PDF parse error: {e}")


def parse_docx(file) -> str:
    try:
        doc = docx.Document(file)
        return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        raise Exception(f"DOCX parse error: {e}")


def parse_txt(file) -> str:
    try:
        raw = file.read()
        return (raw.decode('utf-8') if isinstance(raw, bytes) else raw).strip()
    except Exception as e:
        raise Exception(f"TXT parse error: {e}")


def parse_cv(file) -> Dict:
    name = file.name.lower()
    if name.endswith('.pdf'):
        text = parse_pdf(file)
    elif name.endswith(('.docx', '.doc')):
        text = parse_docx(file)
    elif name.endswith('.txt'):
        text = parse_txt(file)
    else:
        raise Exception("Unsupported format. Use PDF, DOC, DOCX, or TXT.")

    return {
        'raw_text': text,
        'name': _extract_name(text),
        'email': _extract_email(text),
        'phone': _extract_phone(text),
        'skills': _extract_skills(text),
        'experience': _extract_experience(text),
        'education': _extract_education(text),
    }


# ─────────────────────────────────────────────
# EXTRACTION HELPERS
# ─────────────────────────────────────────────

def _extract_name(text: str) -> str:
    for line in (l.strip() for l in text.split('\n') if l.strip()):
        if 2 <= len(line.split()) <= 4 and '@' not in line and len(line) > 3:
            # skip lines that look like headers or dates
            if not re.match(r'(?i)(experience|education|skills|summary|objective|contact)', line):
                return line
    return "Professional"


def _extract_email(text: str) -> str:
    m = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
    return m.group(0) if m else ""


def _extract_phone(text: str) -> str:
    m = re.search(r'(\+?\d{1,3}[\-.\s]?)?(\(?\d{2,4}\)?[\-.\s]?)?\d{3,4}[\-.\s]?\d{4}', text)
    return m.group(0) if m else ""


SKILL_KEYWORDS = [
    'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue.js',
    'node.js', 'express', 'next.js', 'nuxt', 'svelte',
    'sql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch', 'cassandra',
    'docker', 'kubernetes', 'terraform', 'ansible',
    'aws', 'azure', 'gcp', 'google cloud',
    'git', 'github', 'gitlab', 'bitbucket', 'ci/cd', 'jenkins', 'github actions',
    'machine learning', 'deep learning', 'nlp', 'computer vision',
    'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'matplotlib',
    'html', 'css', 'sass', 'less', 'bootstrap', 'tailwind css', 'material ui',
    'django', 'flask', 'fastapi', 'spring boot', 'laravel', 'ruby on rails',
    'rest api', 'graphql', 'microservices', 'websocket',
    'agile', 'scrum', 'kanban', 'jira', 'confluence',
    'linux', 'bash', 'shell scripting', 'powershell',
    'c++', 'c#', '.net', 'go', 'golang', 'rust', 'swift', 'kotlin',
    'react native', 'flutter', 'xamarin',
    'kafka', 'rabbitmq', 'celery', 'aws lambda',
    'power bi', 'tableau', 'excel', 'data analysis', 'data science',
    'project management', 'leadership', 'communication', 'teamwork',
    'problem solving', 'critical thinking', 'time management',
    'figma', 'adobe xd', 'ui/ux', 'wireframing', 'prototyping',
    'aws s3', 'ec2', 'dynamodb', 'azure devops',
]


def _extract_skills(text: str) -> List[str]:
    lower = text.lower()
    found = []
    for kw in SKILL_KEYWORDS:
        if kw in lower:
            found.append(kw.title())
    # deduplicate, preserve order
    seen = set()
    unique = []
    for s in found:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return sorted(unique)


def _extract_experience(text: str) -> List[Dict]:
    exp_header = re.search(
        r'(?i)(work\s*experience|professional\s*experience|employment|experience\s*&?\s*history)',
        text
    )
    if not exp_header:
        return [{'title': 'Professional Experience', 'description': 'See CV for details.'}]

    start = exp_header.end()
    next_sec = re.search(r'(?i)\n(education|skills|certifications|projects|awards)', text[start:])
    chunk = text[start: start + next_sec.start() if next_sec else len(text)]

    entries = []
    for line in (l.strip() for l in chunk.split('\n') if l.strip()):
        if len(line) > 8:
            entries.append({'title': line[:120], 'description': ''})
        if len(entries) >= 5:
            break

    # pair up title / description
    paired = []
    i = 0
    while i < len(entries):
        title = entries[i]['title']
        desc = entries[i + 1]['title'] if i + 1 < len(entries) and len(entries[i + 1]['title']) > 20 else ''
        paired.append({'title': title, 'description': desc})
        i += 2 if desc else 1

    return paired if paired else [{'title': 'Professional Experience', 'description': 'See CV for details.'}]


def _extract_education(text: str) -> List[str]:
    edu = []
    for kw in [r"bachelor", r"master", r"phd", r"doctorate", r"b\.?s\.?", r"m\.?s\.?", r"b\.?a\.?", r"m\.?a\.?", r"mba"]:
        for m in re.finditer(kw, text, re.IGNORECASE):
            ctx = text[max(0, m.start() - 40): min(len(text), m.end() + 120)].strip()
            edu.append(ctx)
    return edu if edu else ["Education details in CV"]


# ─────────────────────────────────────────────
# LINKEDIN (limited — public pages only)
# ─────────────────────────────────────────────

def parse_linkedin(url: str) -> Dict:
    if 'linkedin.com' not in url:
        raise Exception("Please provide a valid linkedin.com URL.")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # LinkedIn blocks most scraping; extract what's in the og/meta tags
        name = (soup.find('meta', {'property': 'og:title'}) or {}).get('content', 'LinkedIn User')
        desc = (soup.find('meta', {'property': 'og:description'}) or {}).get('content', '')

        # pull any visible skill-like text
        body_text = soup.get_text(separator=' ', strip=True)
        skills = _extract_skills(body_text)

        return {
            'name': name.split('|')[0].strip() if name else 'LinkedIn User',
            'email': '',
            'phone': '',
            'skills': skills if skills else ['Communication', 'Teamwork', 'Leadership'],
            'experience': [{'title': 'See LinkedIn for full experience', 'description': desc[:200]}],
            'education': ['See LinkedIn for education details'],
            'raw_text': body_text,
            'note': 'LinkedIn limits automated access. Upload your CV for full analysis.'
        }
    except requests.exceptions.RequestException as e:
        raise Exception(f"Could not reach LinkedIn ({e}). Paste your CV instead.")


# ─────────────────────────────────────────────
# ATS ANALYSIS
# ─────────────────────────────────────────────

def analyze_ats(cv_data: Dict, job_description: str) -> Dict:
    cv_lower = cv_data.get('raw_text', '').lower()
    job_lower = job_description.lower()

    job_kws = _extract_job_keywords(job_lower)
    matched, missing = [], []

    for kw in job_kws:
        if kw in cv_lower:
            matched.append(kw)
        else:
            missing.append(kw)

    score = round((len(matched) / len(job_kws)) * 100) if job_kws else 50
    # clamp
    score = max(0, min(100, score))

    tips = _generate_tips(cv_data, missing, cv_lower)

    return {
        'score': score,
        'matched_skills': matched,
        'missing_skills': missing[:10],
        'tips': tips,
    }


def _extract_job_keywords(job_text: str) -> List[str]:
    found = []
    for kw in SKILL_KEYWORDS:
        if kw in job_text:
            found.append(kw)
    # also grab "X+ years"
    for m in re.finditer(r'(\d+)\+?\s*years?', job_text):
        found.append(f"{m.group(1)}+ years experience")
    return found


def _generate_tips(cv_data: Dict, missing: List[str], cv_lower: str) -> List[str]:
    tips = []

    # top missing skills with free resources
    resource_map = {
        'docker': 'Docker Official Docs + Play With Docker (free)',
        'aws': 'AWS Free Tier + freeCodeCamp AWS Course',
        'kubernetes': 'Kubernetes.io Interactive Tutorial (free)',
        'python': 'Python.org Tutorial + freeCodeCamp',
        'javascript': 'freeCodeCamp + JavaScript.info',
        'react': 'React.dev official tutorial (free)',
        'sql': 'SQLBolt + W3Schools SQL',
        'git': 'GitHub Learning Lab (free)',
        'typescript': 'TypeScript Handbook (official, free)',
        'machine learning': 'Andrew Ng ML Course on Coursera (audit free)',
    }
    for skill in missing[:4]:
        res = resource_map.get(skill.lower(), 'YouTube tutorials + freeCodeCamp')
        tips.append(f"Add \"{skill.title()}\" — Learn via: {res} (~2-4 hrs)")

    if 'project' not in cv_lower:
        tips.append("Add a 'Projects' section — concrete examples boost ATS and recruiter trust.")
    if not any(v in cv_lower for v in ['increased', 'improved', 'reduced', 'grew', '%']):
        tips.append("Include quantifiable achievements (e.g., 'Reduced load time by 40%').")
    if 'certification' not in cv_lower and 'certified' not in cv_lower:
        tips.append("Add certifications — even free ones (Google, AWS, Meta) add credibility.")
    if not any(v in cv_lower for v in ['developed', 'led', 'designed', 'built', 'implemented']):
        tips.append("Use strong action verbs: Developed, Led, Architected, Implemented.")
    if len(cv_data.get('skills', [])) < 6:
        tips.append("Expand your Skills section — aim for 8-12 listed skills.")

    return tips[:8]


# ─────────────────────────────────────────────
# SKILLS ROADMAP
# ─────────────────────────────────────────────

ROADMAP_DB = {
    'python':          {'weeks': '3-5', 'resources': ['Python.org Tutorial', 'freeCodeCamp Python', 'Codecademy']},
    'javascript':      {'weeks': '4-6', 'resources': ['freeCodeCamp JS', 'JavaScript.info', 'MDN Web Docs']},
    'typescript':      {'weeks': '2-3', 'resources': ['TypeScript Handbook', 'freeCodeCamp TS', 'Udemy (free coupons)']},
    'react':           {'weeks': '3-4', 'resources': ['React.dev Tutorial', 'freeCodeCamp React', 'Scrimba (free tier)']},
    'node.js':         {'weeks': '3-4', 'resources': ['Node.js Docs', 'freeCodeCamp Node', 'The Odin Project']},
    'docker':          {'weeks': '2-3', 'resources': ['Docker Docs', 'Play With Docker', 'YouTube: Docker in 1 Hr']},
    'kubernetes':      {'weeks': '4-6', 'resources': ['Kubernetes.io Tutorial', 'KodeKloud (free)', 'CNCF Landscape']},
    'aws':             {'weeks': '6-8', 'resources': ['AWS Free Tier', 'freeCodeCamp AWS', 'A Cloud Guru (free tier)']},
    'azure':           {'weeks': '5-7', 'resources': ['Microsoft Learn', 'Azure Free Tier', 'YouTube: Azure in 1 Hr']},
    'gcp':             {'weeks': '5-7', 'resources': ['Google Cloud Skills Boost', 'GCP Free Tier', 'Qwiklabs']},
    'sql':             {'weeks': '2-3', 'resources': ['SQLBolt', 'W3Schools SQL', 'Khan Academy']},
    'git':             {'weeks': '1-2', 'resources': ['Git-SCM.com', 'GitHub Learning Lab', 'Atlassian Git Tutorial']},
    'machine learning':{'weeks': '8-12','resources': ['Andrew Ng ML (Coursera audit)', 'fast.ai', 'Kaggle Learn']},
    'data science':    {'weeks': '6-8', 'resources': ['Kaggle Learn', 'freeCodeCamp Data Science', 'pandas Docs']},
    'ci/cd':           {'weeks': '2-3', 'resources': ['GitHub Actions Docs', 'Jenkins Tutorials', 'GitLab CI Docs']},
    'linux':           {'weeks': '3-4', 'resources': ['The Linux Command Line (book)', 'Over The Wire Bandit', 'Linux Journey']},
}


def generate_skills_roadmap(missing_skills: List[str]) -> str:
    md = "# 📚 Personalized Skills Roadmap\n\n"
    md += f"*Generated on {datetime.datetime.now().strftime('%B %d, %Y')}*\n\n"
    md += "---\n\n"

    for i, skill in enumerate(missing_skills[:8], 1):
        info = ROADMAP_DB.get(skill.lower(), {'weeks': '2-4', 'resources': ['YouTube Tutorials', 'freeCodeCamp', 'Udemy (free coupons)']})
        md += f"## {i}. {skill.title()}\n\n"
        md += f"⏱️ **Estimated Time:** {info['weeks']} weeks\n\n"
        md += "📖 **Free Resources:**\n"
        for r in info['resources']:
            md += f"  - {r}\n"
        md += "\n✅ **Action Plan:**\n"
        md += f"  1. **Week 1** — Complete a beginner tutorial on {skill.title()}\n"
        md += f"  2. **Week 2** — Build a small hands-on project using {skill.title()}\n"
        md += f"  3. **Week 3+** — Add the project to your GitHub & update your CV\n\n"
        md += "---\n\n"

    md += "> 💡 **Tip:** Focus on 2-3 skills at a time. Consistency beats intensity.\n"
    return md


# ─────────────────────────────────────────────
# CV PDF GENERATION (ReportLab)
# ─────────────────────────────────────────────

def generate_optimized_cv(cv_data: Dict, job_description: str = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.55 * inch, bottomMargin=0.5 * inch,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch
    )
    styles = getSampleStyleSheet()
    story = []

    # ── colour palette ──
    dark = HexColor('#1a1a2e')
    accent = HexColor('#e94560')
    mid = HexColor('#16213e')
    grey = HexColor('#555555')

    # ── custom styles ──
    name_style = ParagraphStyle('Name', parent=styles['Normal'],
                                fontSize=26, textColor=dark, alignment=TA_CENTER,
                                fontName='Helvetica-Bold', spaceAfter=2)
    contact_style = ParagraphStyle('Contact', parent=styles['Normal'],
                                   fontSize=9, textColor=grey, alignment=TA_CENTER,
                                   fontName='Helvetica', spaceAfter=4)
    section_style = ParagraphStyle('Section', parent=styles['Normal'],
                                   fontSize=11, textColor=accent,
                                   fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                fontSize=9.5, textColor=dark,
                                fontName='Helvetica', spaceAfter=3, leading=13)
    bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'],
                                  fontSize=9, textColor=grey,
                                  fontName='Helvetica', leftIndent=14, spaceAfter=2, leading=12)

    # ── NAME ──
    story.append(Paragraph(cv_data.get('name', 'Professional Resume'), name_style))

    # ── CONTACT LINE ──
    parts = []
    if cv_data.get('email'):  parts.append(cv_data['email'])
    if cv_data.get('phone'):  parts.append(cv_data['phone'])
    if parts:
        story.append(Paragraph(' • '.join(parts), contact_style))
    story.append(HRFlowable(width="100%", color=accent, thickness=1.5, spaceAfter=6))

    # ── PROFESSIONAL SUMMARY ──
    skills_preview = ', '.join(cv_data.get('skills', [])[:5]) or 'diverse technologies'
    summary = (
        f"Results-driven professional with hands-on expertise in <b>{skills_preview}</b>. "
        f"Passionate about delivering high-quality, scalable solutions and continuously expanding technical skills. "
        f"Proven track record of collaborating in fast-paced environments to meet and exceed project goals."
    )
    story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
    story.append(Paragraph(summary, body_style))

    # ── SKILLS ──
    if cv_data.get('skills'):
        story.append(Paragraph("SKILLS", section_style))
        # If job desc provided, prioritise matched skills
        all_skills = cv_data['skills']
        story.append(Paragraph(' &nbsp;•&nbsp; '.join(all_skills[:16]), body_style))

    # ── EXPERIENCE ──
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
    for exp in cv_data.get('experience', [])[:5]:
        story.append(Paragraph(f"<b>{exp.get('title', 'Role')}</b>", body_style))
        if exp.get('description'):
            story.append(Paragraph(f"• {exp['description']}", bullet_style))

    # ── EDUCATION ──
    if cv_data.get('education'):
        story.append(Paragraph("EDUCATION", section_style))
        for edu in cv_data['education'][:3]:
            story.append(Paragraph(edu, body_style))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────
# PORTFOLIO HTML + ZIP
# ─────────────────────────────────────────────

def generate_portfolio(cv_data: Dict) -> bytes:
    name = cv_data.get('name', 'Professional')
    email = cv_data.get('email', 'contact@example.com')
    phone = cv_data.get('phone', '')
    skills = cv_data.get('skills', ['Software Development', 'Problem Solving'])
    experience = cv_data.get('experience', [])
    education = cv_data.get('education', [])

    # ── skills grid cards ──
    skill_cards = "\n".join([
        f'''            <div class="skill-card">
              <div class="skill-icon">{s[0].upper()}</div>
              <span>{s}</span>
            </div>'''
        for s in skills[:16]
    ])

    # ── experience timeline items ──
    exp_items = "\n".join([
        f'''            <div class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <h3>{e.get('title', 'Role')}</h3>
                <p>{e.get('description', 'Delivered impactful results in a professional setting.')}</p>
              </div>
            </div>'''
        for e in experience[:5]
    ])

    # ── education list ──
    edu_items = "\n".join([f'            <li>{e}</li>' for e in education[:4]])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{name} — Portfolio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
  <style>
    /* ─── reset & base ─── */
    *, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
    :root {{
      --clr-bg:      #0f1117;
      --clr-surface: #1a1d27;
      --clr-accent:  #e94560;
      --clr-accent2: #c23152;
      --clr-text:    #e2e4e9;
      --clr-muted:   #7a7f8e;
      --font-head:   'Syne', sans-serif;
      --font-body:   'Inter', sans-serif;
    }}
    html {{ scroll-behavior:smooth; }}
    body {{
      font-family: var(--font-body);
      background: var(--clr-bg);
      color: var(--clr-text);
      line-height: 1.6;
      overflow-x: hidden;
    }}

    /* ─── nav ─── */
    nav {{
      position:fixed; top:0; width:100%; z-index:100;
      background:rgba(15,17,23,.85);
      backdrop-filter:blur(12px);
      border-bottom:1px solid rgba(233,69,96,.15);
      padding:.9rem 0;
      transition: background .3s;
    }}
    .nav-inner {{
      max-width:1100px; margin:0 auto; padding:0 1.5rem;
      display:flex; justify-content:space-between; align-items:center;
    }}
    .nav-logo {{
      font-family:var(--font-head); font-size:1.3rem;
      color:#fff; text-decoration:none; letter-spacing:-0.5px;
    }}
    .nav-links a {{
      color:var(--clr-muted); text-decoration:none;
      margin-left:1.8rem; font-size:.85rem; font-weight:500;
      letter-spacing:.5px; text-transform:uppercase;
      transition:color .2s;
    }}
    .nav-links a:hover {{ color:var(--clr-accent); }}

    /* ─── hero ─── */
    .hero {{
      min-height:100vh;
      display:flex; align-items:center; justify-content:center;
      position:relative; overflow:hidden;
      padding:7rem 1.5rem 4rem;
    }}
    .hero-bg {{
      position:absolute; inset:0; z-index:0;
      background:
        radial-gradient(ellipse 80% 50% at 20% 80%, rgba(233,69,96,.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 20%, rgba(26,29,39,.8) 0%, transparent 70%);
    }}
    .hero-content {{
      position:relative; z-index:1;
      text-align:center; max-width:720px;
    }}
    .hero-content h1 {{
      font-family:var(--font-head);
      font-size:clamp(2.8rem,7vw,5.5rem);
      font-weight:800; line-height:1.05;
      letter-spacing:-2px; color:#fff;
      margin-bottom:.6rem;
    }}
    .hero-content h1 span {{ color:var(--clr-accent); }}
    .hero-subtitle {{
      color:var(--clr-muted); font-size:1.1rem; font-weight:300;
      max-width:500px; margin:0 auto 2rem;
    }}
    .btn {{
      display:inline-block; padding:.75rem 2rem;
      background:var(--clr-accent); color:#fff;
      border:none; border-radius:6px;
      font-family:var(--font-body); font-size:.88rem;
      font-weight:600; letter-spacing:.4px; text-transform:uppercase;
      text-decoration:none; cursor:pointer;
      transition:background .25s, transform .2s;
    }}
    .btn:hover {{ background:var(--clr-accent2); transform:translateY(-2px); }}

    /* ─── sections common ─── */
    section {{ padding:6rem 1.5rem; }}
    .container {{ max-width:1050px; margin:0 auto; }}
    .section-label {{
      font-size:.75rem; color:var(--clr-accent);
      letter-spacing:3px; text-transform:uppercase;
      font-weight:600; margin-bottom:.5rem;
    }}
    .section-title {{
      font-family:var(--font-head); font-size:clamp(1.8rem,4vw,2.6rem);
      font-weight:800; color:#fff; margin-bottom:2.5rem;
      letter-spacing:-1px;
    }}

    /* ─── about ─── */
    #about {{ background:var(--clr-surface); }}
    .about-grid {{
      display:grid; grid-template-columns:1fr 1fr; gap:3rem;
      align-items:center;
    }}
    .about-text p {{
      color:var(--clr-muted); font-size:1rem; margin-bottom:1rem;
    }}
    .about-stats {{
      display:grid; grid-template-columns:1fr 1fr; gap:1.2rem;
    }}
    .stat-card {{
      background:var(--clr-bg); border:1px solid rgba(233,69,96,.15);
      border-radius:10px; padding:1.4rem; text-align:center;
    }}
    .stat-card .num {{
      font-family:var(--font-head); font-size:1.9rem;
      color:var(--clr-accent); font-weight:800;
    }}
    .stat-card .label {{
      color:var(--clr-muted); font-size:.78rem; margin-top:.2rem;
      text-transform:uppercase; letter-spacing:1px;
    }}

    /* ─── skills ─── */
    .skills-grid {{
      display:grid;
      grid-template-columns:repeat(auto-fill, minmax(140px,1fr));
      gap:1rem;
    }}
    .skill-card {{
      background:var(--clr-surface);
      border:1px solid rgba(233,69,96,.1);
      border-radius:10px; padding:1.3rem .8rem;
      text-align:center; transition:transform .2s, border-color .2s;
    }}
    .skill-card:hover {{
      transform:translateY(-3px);
      border-color:var(--clr-accent);
    }}
    .skill-icon {{
      width:36px; height:36px; border-radius:8px;
      background:linear-gradient(135deg, var(--clr-accent), var(--clr-accent2));
      color:#fff; font-weight:700; font-size:1rem;
      display:flex; align-items:center; justify-content:center;
      margin:0 auto .6rem;
    }}
    .skill-card span {{
      font-size:.82rem; color:var(--clr-muted); font-weight:500;
    }}

    /* ─── experience timeline ─── */
    #experience {{ background:var(--clr-surface); }}
    .timeline {{ position:relative; padding-left:2rem; }}
    .timeline::before {{
      content:''; position:absolute; left:.75rem; top:0; bottom:0;
      width:2px; background:rgba(233,69,96,.25);
    }}
    .timeline-item {{ position:relative; margin-bottom:2rem; }}
    .timeline-dot {{
      position:absolute; left:-1.3rem; top:.35rem;
      width:12px; height:12px; border-radius:50%;
      background:var(--clr-accent);
      box-shadow:0 0 8px rgba(233,69,96,.4);
    }}
    .timeline-content {{
      background:var(--clr-bg); border:1px solid rgba(233,69,96,.1);
      border-radius:10px; padding:1.3rem 1.5rem;
    }}
    .timeline-content h3 {{
      color:#fff; font-size:1rem; font-weight:600; margin-bottom:.3rem;
    }}
    .timeline-content p {{
      color:var(--clr-muted); font-size:.85rem;
    }}

    /* ─── education ─── */
    .edu-list {{
      list-style:none; padding:0;
    }}
    .edu-list li {{
      background:var(--clr-surface); border:1px solid rgba(233,69,96,.1);
      border-radius:10px; padding:1rem 1.4rem; margin-bottom:.7rem;
      color:var(--clr-muted); font-size:.9rem;
    }}
    .edu-list li::before {{
      content:'🎓 '; 
    }}

    /* ─── contact ─── */
    #contact {{
      background:linear-gradient(135deg, #12151f 0%, #1a1d27 100%);
      text-align:center;
    }}
    .contact-info {{
      display:flex; justify-content:center; gap:2.5rem;
      flex-wrap:wrap; margin-top:1.5rem;
    }}
    .contact-item {{
      color:var(--clr-muted); font-size:.9rem;
    }}
    .contact-item strong {{ color:#fff; }}

    /* ─── footer ─── */
    footer {{
      text-align:center; padding:2rem;
      color:var(--clr-muted); font-size:.78rem;
      border-top:1px solid rgba(255,255,255,.06);
    }}

    /* ─── responsive ─── */
    @media (max-width:680px) {{
      .about-grid {{ grid-template-columns:1fr; }}
      .nav-links a {{ margin-left:.9rem; font-size:.75rem; }}
      .skills-grid {{ grid-template-columns:repeat(auto-fill, minmax(110px,1fr)); }}
    }}

    /* ─── animations ─── */
    @keyframes fadeUp {{
      from {{ opacity:0; transform:translateY(24px); }}
      to   {{ opacity:1; transform:translateY(0); }}
    }}
    .fade-up {{ animation:fadeUp .6s ease both; }}
    .delay-1 {{ animation-delay:.1s; }}
    .delay-2 {{ animation-delay:.2s; }}
    .delay-3 {{ animation-delay:.35s; }}
  </style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="nav-inner">
    <a href="#" class="nav-logo">{name}</a>
    <div class="nav-links">
      <a href="#about">About</a>
      <a href="#skills">Skills</a>
      <a href="#experience">Experience</a>
      <a href="#contact">Contact</a>
    </div>
  </div>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-content fade-up">
    <h1>Hi, I'm <span>{name}</span></h1>
    <p class="hero-subtitle">
      A passionate professional crafting innovative solutions and delivering exceptional results.
    </p>
    <a href="#contact" class="btn">Get In Touch</a>
  </div>
</section>

<!-- ABOUT -->
<section id="about">
  <div class="container">
    <div class="about-grid">
      <div class="about-text fade-up">
        <p class="section-label">About Me</p>
        <h2 class="section-title">Building things<br/>that matter.</h2>
        <p>
          Results-driven professional with deep expertise in {', '.join(skills[:3])}.
          I thrive on solving complex problems and turning ideas into polished, scalable products.
        </p>
        <p>
          Passionate about continuous learning, clean code, and creating experiences
          that delight users. Always looking for the next challenge.
        </p>
      </div>
      <div class="about-stats fade-up delay-2">
        <div class="stat-card">
          <div class="num">{len(skills)}</div>
          <div class="label">Skills</div>
        </div>
        <div class="stat-card">
          <div class="num">{len(experience)}</div>
          <div class="label">Roles</div>
        </div>
        <div class="stat-card">
          <div class="num">{len(education)}</div>
          <div class="label">Education</div>
        </div>
        <div class="stat-card">
          <div class="num">∞</div>
          <div class="label">Curiosity</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- SKILLS -->
<section id="skills">
  <div class="container">
    <p class="section-label fade-up">Expertise</p>
    <h2 class="section-title fade-up delay-1">Skills & Tools</h2>
    <div class="skills-grid fade-up delay-2">
{skill_cards}
    </div>
  </div>
</section>

<!-- EXPERIENCE -->
<section id="experience">
  <div class="container">
    <p class="section-label fade-up">Career</p>
    <h2 class="section-title fade-up delay-1">Experience</h2>
    <div class="timeline fade-up delay-2">
{exp_items}
    </div>
  </div>
</section>

<!-- EDUCATION -->
<section id="education">
  <div class="container">
    <p class="section-label fade-up">Learning</p>
    <h2 class="section-title fade-up delay-1">Education</h2>
    <ul class="edu-list fade-up delay-2">
{edu_items}
    </ul>
  </div>
</section>

<!-- CONTACT -->
<section id="contact">
  <div class="container">
    <p class="section-label fade-up">Let's connect</p>
    <h2 class="section-title fade-up delay-1">Get In Touch</h2>
    <p class="fade-up delay-2" style="color:var(--clr-muted); max-width:480px; margin:0 auto;">
      Interested in working together or just want to say hi? I'd love to hear from you.
    </p>
    <div class="contact-info fade-up delay-3">
      <div class="contact-item">📧 <strong>{email}</strong></div>
      {"<div class='contact-item'>📱 <strong>" + phone + "</strong></div>" if phone else ""}
    </div>
  </div>
</section>

<!-- FOOTER -->
<footer>
  <p>&copy; {datetime.datetime.now().year} {name} — Portfolio generated by CareerBoost AI</p>
</footer>

</body>
</html>"""

    # ── package into ZIP ──
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('index.html', html)
        zf.writestr('README.md',
            f"# {name} — Portfolio\n\n"
            f"Generated by CareerBoost AI on {datetime.datetime.now().strftime('%Y-%m-%d')}.\n\n"
            f"## Deploy (all free)\n"
            f"1. **GitHub Pages** — push to a repo, enable Pages\n"
            f"2. **Netlify** — drag & drop the folder\n"
            f"3. **Vercel** — connect your GitHub repo\n"
        )
    buf.seek(0)
    return buf.getvalue()
