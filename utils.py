import fitz  # PyMuPDF
import docx
import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import markdown2
import re
import json
from typing import Dict, List, Tuple
import io
import zipfile

def parse_pdf(file) -> str:
    """Extract text from PDF using PyMuPDF"""
    try:
        pdf_bytes = file.read()
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text += page.get_text()
        pdf_document.close()
        return text.strip()
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")

def parse_docx(file) -> str:
    """Extract text from DOCX"""
    try:
        doc = docx.Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise Exception(f"Error parsing DOCX: {str(e)}")

def parse_txt(file) -> str:
    """Extract text from TXT"""
    try:
        text = file.read().decode('utf-8')
        return text.strip()
    except Exception as e:
        raise Exception(f"Error parsing TXT: {str(e)}")

def parse_cv(file) -> Dict:
    """Parse CV and extract structured information"""
    filename = file.name.lower()
    
    if filename.endswith('.pdf'):
        text = parse_pdf(file)
    elif filename.endswith('.docx') or filename.endswith('.doc'):
        text = parse_docx(file)
    elif filename.endswith('.txt'):
        text = parse_txt(file)
    else:
        raise Exception("Unsupported file format. Please upload PDF, DOC, DOCX, or TXT.")
    
    # Extract structured data using regex patterns
    data = {
        'raw_text': text,
        'name': extract_name(text),
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills(text),
        'experience': extract_experience(text),
        'education': extract_education(text)
    }
    
    return data

def extract_name(text: str) -> str:
    """Extract name from CV text (first line heuristic)"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        # Often the name is in the first few lines
        for line in lines[:3]:
            if len(line.split()) <= 4 and len(line) > 3 and not '@' in line:
                return line
    return "Not Found"

def extract_email(text: str) -> str:
    """Extract email address"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    return match.group(0) if match else "Not Found"

def extract_phone(text: str) -> str:
    """Extract phone number"""
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    match = re.search(phone_pattern, text)
    return match.group(0) if match else "Not Found"

def extract_skills(text: str) -> List[str]:
    """Extract skills using keyword matching"""
    # Common skill keywords
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
        'sql', 'mongodb', 'postgresql', 'mysql', 'docker', 'kubernetes',
        'aws', 'azure', 'gcp', 'git', 'machine learning', 'deep learning',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
        'html', 'css', 'bootstrap', 'tailwind', 'django', 'flask', 'fastapi',
        'rest api', 'graphql', 'agile', 'scrum', 'ci/cd', 'jenkins',
        'linux', 'bash', 'c++', 'c#', '.net', 'go', 'rust', 'typescript',
        'express', 'spring boot', 'microservices', 'redis', 'elasticsearch'
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in skill_keywords:
        if skill in text_lower:
            # Capitalize properly
            found_skills.append(skill.title())
    
    # Remove duplicates and sort
    return sorted(list(set(found_skills)))

def extract_experience(text: str) -> List[Dict]:
    """Extract work experience"""
    experience = []
    
    # Look for common experience section headers
    exp_patterns = [
        r'(?i)(work experience|professional experience|employment history|experience)',
        r'(?i)(work history)'
    ]
    
    for pattern in exp_patterns:
        match = re.search(pattern, text)
        if match:
            # Get text after the header
            start_pos = match.end()
            # Find next section (education, skills, etc.)
            next_section = re.search(r'(?i)(education|skills|certifications|projects)', text[start_pos:])
            end_pos = next_section.start() + start_pos if next_section else len(text)
            
            exp_text = text[start_pos:end_pos]
            
            # Extract individual experiences (simplified)
            lines = [line.strip() for line in exp_text.split('\n') if line.strip()]
            for i, line in enumerate(lines[:5]):  # Get first 5 entries
                if len(line) > 10:
                    experience.append({
                        'title': line[:100],
                        'description': lines[i+1] if i+1 < len(lines) else ""
                    })
            break
    
    return experience if experience else [{'title': 'Experience details found in CV', 'description': ''}]

def extract_education(text: str) -> List[str]:
    """Extract education information"""
    education = []
    
    # Common degree keywords
    degree_keywords = [
        r"bachelor['\"]?s?", r"master['\"]?s?", r"phd", r"doctorate",
        r"b\.?s\.?", r"m\.?s\.?", r"b\.?a\.?", r"m\.?a\.?", r"mba"
    ]
    
    text_lower = text.lower()
    
    for keyword in degree_keywords:
        matches = re.finditer(keyword, text_lower)
        for match in matches:
            # Get context around the match
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 100)
            context = text[start:end].strip()
            education.append(context)
    
    return education if education else ["Education details found in CV"]

def parse_linkedin(url: str) -> Dict:
    """Parse public LinkedIn profile (basic info only - no login)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # LinkedIn blocks scraping, so we get limited info
        # This is a simplified version - real implementation would need more robust parsing
        
        data = {
            'name': 'LinkedIn Profile',
            'headline': 'Professional Profile',
            'skills': ['LinkedIn', 'Professional Networking', 'Communication'],
            'experience': [{'title': 'See LinkedIn profile for details', 'description': ''}],
            'education': ['See LinkedIn profile for details'],
            'note': 'LinkedIn limits public data access. Please upload your CV for detailed analysis.'
        }
        
        return data
        
    except Exception as e:
        raise Exception(f"Error parsing LinkedIn URL: {str(e)}. LinkedIn restricts automated access. Please upload your CV instead.")

def analyze_ats(cv_data: Dict, job_description: str) -> Dict:
    """Analyze ATS score and provide recommendations"""
    cv_text = cv_data.get('raw_text', '').lower()
    job_text = job_description.lower()
    
    # Extract keywords from job description
    job_keywords = extract_job_keywords(job_text)
    cv_skills = [skill.lower() for skill in cv_data.get('skills', [])]
    
    # Calculate matching score
    matched_keywords = []
    missing_keywords = []
    
    for keyword in job_keywords:
        if keyword in cv_text or keyword in ' '.join(cv_skills):
            matched_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    # Calculate ATS score
    if job_keywords:
        ats_score = int((len(matched_keywords) / len(job_keywords)) * 100)
    else:
        ats_score = 50
    
    # Generate tips
    tips = generate_tips(cv_data, missing_keywords, cv_text)
    
    return {
        'score': ats_score,
        'matched_skills': matched_keywords,
        'missing_skills': missing_keywords[:10],  # Top 10 missing
        'tips': tips
    }

def extract_job_keywords(job_text: str) -> List[str]:
    """Extract important keywords from job description"""
    # Common technical and professional keywords
    all_keywords = [
        'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
        'sql', 'mongodb', 'postgresql', 'docker', 'kubernetes', 'aws', 'azure',
        'machine learning', 'data analysis', 'agile', 'scrum', 'git',
        'leadership', 'communication', 'teamwork', 'problem solving',
        'project management', 'rest api', 'microservices', 'ci/cd',
        'typescript', 'html', 'css', 'flask', 'django', 'spring boot',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'excel', 'tableau',
        'power bi', 'linux', 'bash', 'redis', 'elasticsearch', 'kafka'
    ]
    
    found_keywords = []
    for keyword in all_keywords:
        if keyword in job_text:
            found_keywords.append(keyword)
    
    # Also extract years of experience requirements
    exp_match = re.search(r'(\d+)\+?\s*years?', job_text)
    if exp_match:
        found_keywords.append(f"{exp_match.group(1)}+ years experience")
    
    return found_keywords

def generate_tips(cv_data: Dict, missing_skills: List[str], cv_text: str) -> List[str]:
    """Generate actionable improvement tips"""
    tips = []
    
    # Skill gaps
    if missing_skills:
        top_missing = missing_skills[:3]
        for skill in top_missing:
            tips.append(f"Add '{skill.title()}' skill - Learn via freeCodeCamp or Coursera (2-4 hours)")
    
    # CV structure tips
    if 'projects' not in cv_text and 'project' not in cv_text:
        tips.append("Add a 'Projects' section to showcase practical experience")
    
    if 'achievement' not in cv_text and 'accomplish' not in cv_text:
        tips.append("Include quantifiable achievements (e.g., 'Increased efficiency by 30%')")
    
    if len(cv_data.get('skills', [])) < 5:
        tips.append("Expand your skills section with both technical and soft skills")
    
    if 'certification' not in cv_text:
        tips.append("Add relevant certifications to boost credibility")
    
    # Action verb check
    action_verbs = ['developed', 'created', 'managed', 'led', 'designed', 'implemented']
    if not any(verb in cv_text for verb in action_verbs):
        tips.append("Use strong action verbs (Developed, Led, Implemented) in experience descriptions")
    
    return tips[:8]  # Return top 8 tips

def generate_optimized_cv(cv_data: Dict, job_description: str = None) -> bytes:
    """Generate ATS-optimized CV as PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#2C3E50',
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#34495E',
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    # Header
    name = cv_data.get('name', 'Professional Resume')
    story.append(Paragraph(name, title_style))
    
    contact_info = f"{cv_data.get('email', '')} | {cv_data.get('phone', '')}"
    story.append(Paragraph(contact_info, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Professional Summary
    story.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
    summary = "Results-driven professional with proven expertise in delivering high-quality solutions. "
    summary += f"Skilled in {', '.join(cv_data.get('skills', [])[:5])}. "
    summary += "Committed to continuous learning and excellence in every project."
    story.append(Paragraph(summary, normal_style))
    story.append(Spacer(1, 0.15*inch))
    
    # Skills
    if cv_data.get('skills'):
        story.append(Paragraph("SKILLS", heading_style))
        skills_text = " • ".join(cv_data['skills'][:15])
        story.append(Paragraph(skills_text, normal_style))
        story.append(Spacer(1, 0.15*inch))
    
    # Experience
    if cv_data.get('experience'):
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", heading_style))
        for exp in cv_data['experience'][:4]:
            story.append(Paragraph(f"<b>{exp.get('title', '')}</b>", normal_style))
            if exp.get('description'):
                story.append(Paragraph(f"• {exp['description']}", normal_style))
        story.append(Spacer(1, 0.15*inch))
    
    # Education
    if cv_data.get('education'):
        story.append(Paragraph("EDUCATION", heading_style))
        for edu in cv_data['education'][:3]:
            story.append(Paragraph(edu, normal_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_portfolio(cv_data: Dict) -> bytes:
    """Generate portfolio website as HTML/ZIP with Tailwind CSS"""
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cv_data.get('name', 'Professional Portfolio')}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .fade-in {{ animation: fadeIn 0.6s ease-out; }}
    </style>
</head>
<body class="bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-lg fixed w-full z-10">
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center py-4">
                <div class="text-2xl font-bold text-blue-600">{cv_data.get('name', 'Portfolio')}</div>
                <div class="hidden md:flex space-x-6">
                    <a href="#about" class="text-gray-700 hover:text-blue-600 transition">About</a>
                    <a href="#skills" class="text-gray-700 hover:text-blue-600 transition">Skills</a>
                    <a href="#experience" class="text-gray-700 hover:text-blue-600 transition">Experience</a>
                    <a href="#contact" class="text-gray-700 hover:text-blue-600 transition">Contact</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-r from-blue-500 to-purple-600 text-white">
        <div class="max-w-6xl mx-auto px-4 text-center fade-in">
            <h1 class="text-5xl md:text-6xl font-bold mb-4">{cv_data.get('name', 'Professional Portfolio')}</h1>
            <p class="text-xl md:text-2xl mb-8">Passionate Developer | Problem Solver | Innovator</p>
            <a href="#contact" class="bg-white text-blue-600 px-8 py-3 rounded-full font-semibold hover:bg-gray-100 transition">Get In Touch</a>
        </div>
    </section>

    <!-- About Section -->
    <section id="about" class="py-20">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-4xl font-bold text-center mb-12 text-gray-800">About Me</h2>
            <div class="bg-white rounded-lg shadow-lg p-8 fade-in">
                <p class="text-lg text-gray-700 leading-relaxed">
                    Results-driven professional with expertise in modern technologies and a passion for creating 
                    innovative solutions. Committed to continuous learning and delivering high-quality work that 
                    exceeds expectations. Strong background in {', '.join(cv_data.get('skills', ['software development'])[:3])}.
                </p>
            </div>
        </div>
    </section>

    <!-- Skills Section -->
    <section id="skills" class="py-20 bg-gray-100">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-4xl font-bold text-center mb-12 text-gray-800">Skills & Expertise</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                {''.join([f'<div class="bg-white rounded-lg shadow p-4 text-center hover:shadow-lg transition"><span class="text-blue-600 font-semibold">{skill}</span></div>' for skill in cv_data.get('skills', ['Python', 'JavaScript', 'React', 'Node.js'])[:12]])}
            </div>
        </div>
    </section>

    <!-- Experience Section -->
    <section id="experience" class="py-20">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-4xl font-bold text-center mb-12 text-gray-800">Experience</h2>
            <div class="space-y-6">
                {''.join([f'''<div class="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition">
                    <h3 class="text-xl font-bold text-gray-800 mb-2">{exp.get('title', 'Professional Experience')}</h3>
                    <p class="text-gray-600">{exp.get('description', 'Delivered exceptional results in a professional environment.')}</p>
                </div>''' for exp in cv_data.get('experience', [{'title': 'Professional Experience', 'description': 'Proven track record of success'}])[:4]])}
            </div>
        </div>
    </section>

    <!-- Contact Section -->
    <section id="contact" class="py-20 bg-gradient-to-r from-purple-600 to-blue-500 text-white">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <h2 class="text-4xl font-bold mb-8">Let's Connect</h2>
            <p class="text-xl mb-8">Interested in working together? Reach out!</p>
            <div class="space-y-4">
                <p class="text-lg">📧 Email: {cv_data.get('email', 'contact@example.com')}</p>
                <p class="text-lg">📱 Phone: {cv_data.get('phone', 'Available upon request')}</p>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white py-8">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <p>&copy; 2026 {cv_data.get('name', 'Portfolio')}. All rights reserved.</p>
            <p class="text-sm text-gray-400 mt-2">Generated by CareerBoost AI</p>
        </div>
    </footer>
</body>
</html>"""
    
    # Create ZIP file with HTML
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('index.html', html_content)
        
        # Add a README
        readme = f"""# {cv_data.get('name', 'Professional')} Portfolio

This is a professional portfolio website generated by CareerBoost AI.

## How to Use

1. Extract this ZIP file
2. Open `index.html` in your web browser
3. To deploy online:
   - Upload to GitHub Pages (free)
   - Deploy to Netlify (free)
   - Deploy to Vercel (free)

## Customization

Feel free to edit the HTML file to customize colors, content, and styling.

Generated on: {import datetime; datetime.datetime.now().strftime('%Y-%m-%d')}
"""
        zip_file.writestr('README.md', readme)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def generate_skills_roadmap(missing_skills: List[str]) -> str:
    """Generate a learning roadmap for missing skills"""
    roadmap = "# Skills Development Roadmap\n\n"
    
    # Learning resources mapping
    resources = {
        'python': {'time': '4-6 weeks', 'resources': ['Python.org Tutorial', 'freeCodeCamp', 'Codecademy']},
        'javascript': {'time': '4-6 weeks', 'resources': ['freeCodeCamp', 'JavaScript.info', 'MDN Web Docs']},
        'react': {'time': '3-4 weeks', 'resources': ['React.dev', 'freeCodeCamp', 'Scrimba']},
        'docker': {'time': '2-3 weeks', 'resources': ['Docker Docs', 'Docker Tutorial for Beginners', 'KodeKloud']},
        'aws': {'time': '6-8 weeks', 'resources': ['AWS Free Tier', 'freeCodeCamp AWS Course', 'A Cloud Guru']},
        'sql': {'time': '2-3 weeks', 'resources': ['SQLBolt', 'W3Schools SQL', 'Khan Academy']},
        'git': {'time': '1-2 weeks', 'resources': ['Git-SCM.com', 'GitHub Learning Lab', 'Atlassian Git Tutorial']},
    }
    
    for i, skill in enumerate(missing_skills[:8], 1):
        skill_lower = skill.lower()
        skill_info = resources.get(skill_lower, {'time': '2-4 weeks', 'resources': ['Google Search', 'YouTube Tutorials', 'Udemy']})
        
        roadmap += f"## {i}. {skill.title()}\n\n"
        roadmap += f"**Estimated Time:** {skill_info['time']}\n\n"
        roadmap += "**Free Resources:**\n"
        for resource in skill_info['resources']:
            roadmap += f"- {resource}\n"
        roadmap += "\n**Action Steps:**\n"
        roadmap += f"1. Complete beginner tutorial (Week 1)\n"
        roadmap += f"2. Build a small project using {skill.title()} (Week 2)\n"
        roadmap += f"3. Add project to your CV and GitHub\n\n"
        roadmap += "---\n\n"
    
    return roadmap
