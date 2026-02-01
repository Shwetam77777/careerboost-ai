import streamlit as st
from utils import (
    parse_cv, parse_linkedin, analyze_ats, 
    generate_optimized_cv, generate_portfolio,
    generate_skills_roadmap, parse_pdf, parse_txt
)
import io

# Page config
st.set_page_config(
    page_title="CareerBoost AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .tip-box {
        background-color: #f0f7ff;
        border-left: 4px solid #4299e1;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<div class="main-header">🚀 CareerBoost AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Transform Your Career with AI-Powered CV Optimization & Portfolio Generation</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📤 Upload Your Documents")
        
        # CV Upload
        cv_file = st.file_uploader(
            "Upload CV/Resume",
            type=['pdf', 'doc', 'docx', 'txt'],
            help="Upload your CV in PDF, DOC, DOCX, or TXT format"
        )
        
        # LinkedIn URL
        linkedin_url = st.text_input(
            "LinkedIn Profile URL (Optional)",
            placeholder="https://linkedin.com/in/yourprofile",
            help="Public LinkedIn profile URL"
        )
        
        st.markdown("---")
        
        # Job Description
        st.subheader("🎯 Job Analysis (Optional)")
        job_desc_option = st.radio(
            "Job Description Input",
            ["Paste Text", "Upload PDF", "Paste URL"]
        )
        
        job_description = None
        job_url = None
        job_file = None
        
        if job_desc_option == "Paste Text":
            job_description = st.text_area(
                "Paste Job Description",
                height=200,
                placeholder="Paste the job description here..."
            )
        elif job_desc_option == "Upload PDF":
            job_file = st.file_uploader(
                "Upload Job Description PDF",
                type=['pdf', 'txt'],
                key="job_file"
            )
        else:
            job_url = st.text_input(
                "Job Posting URL",
                placeholder="https://example.com/job/posting"
            )
        
        st.markdown("---")
        
        analyze_button = st.button("🚀 Analyze & Generate", type="primary", use_container_width=True)
    
    # Main content area
    if not analyze_button:
        # Welcome screen
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            ### 📊 ATS Optimization
            - Get your ATS score (0-100%)
            - Identify skill gaps
            - Receive actionable tips
            """)
        
        with col2:
            st.markdown("""
            ### 📄 CV Generation
            - Create ATS-optimized CV
            - Professional formatting
            - Tailored to job requirements
            """)
        
        with col3:
            st.markdown("""
            ### 🌐 Portfolio Website
            - Beautiful HTML portfolio
            - Responsive design
            - Ready to deploy
            """)
        
        st.info("👈 Upload your CV in the sidebar to get started!")
        
    else:
        # Process inputs
        if not cv_file and not linkedin_url:
            st.error("⚠️ Please upload a CV or provide a LinkedIn URL to continue.")
            return
        
        try:
            with st.spinner("🔄 Processing your documents..."):
                # Parse CV
                cv_data = None
                if cv_file:
                    cv_data = parse_cv(cv_file)
                    st.success("✅ CV parsed successfully!")
                
                # Parse LinkedIn (if provided)
                linkedin_data = None
                if linkedin_url:
                    try:
                        linkedin_data = parse_linkedin(linkedin_url)
                        st.info("ℹ️ LinkedIn data extracted (limited due to access restrictions)")
                        # Merge with CV data
                        if cv_data and linkedin_data:
                            cv_data['skills'] = list(set(cv_data['skills'] + linkedin_data.get('skills', [])))
                    except Exception as e:
                        st.warning(f"⚠️ {str(e)}")
                
                # Use CV data or LinkedIn data
                final_data = cv_data if cv_data else linkedin_data
                
                if not final_data:
                    st.error("❌ Unable to extract data from provided sources.")
                    return
                
                # Parse job description
                job_text = None
                if job_description:
                    job_text = job_description
                elif job_file:
                    if job_file.name.endswith('.pdf'):
                        job_text = parse_pdf(job_file)
                    else:
                        job_text = parse_txt(job_file)
                elif job_url:
                    st.warning("⚠️ URL parsing for job descriptions is limited. Please paste the text instead.")
                
                # Create tabs
                if job_text:
                    tab1, tab2, tab3, tab4, tab5 = st.tabs([
                        "📊 ATS Analysis", 
                        "📄 Optimized CV", 
                        "🌐 Portfolio", 
                        "📚 Skills Roadmap",
                        "📋 Extracted Data"
                    ])
                else:
                    tab1, tab2, tab3 = st.tabs([
                        "📄 Optimized CV", 
                        "🌐 Portfolio",
                        "📋 Extracted Data"
                    ])
                
                # ATS Analysis Tab (only if job description provided)
                if job_text:
                    with tab1:
                        st.header("🎯 ATS Score & Analysis")
                        
                        with st.spinner("Analyzing ATS compatibility..."):
                            ats_results = analyze_ats(final_data, job_text)
                        
                        # Score display
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            score = ats_results['score']
                            score_color = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
                            st.markdown(f"""
                            <div class="metric-card">
                                <h2>{score_color} {score}%</h2>
                                <p>ATS Score</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(f"""
                            <div class="metric-card">
                                <h2>✅ {len(ats_results['matched_skills'])}</h2>
                                <p>Matched Skills</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(f"""
                            <div class="metric-card">
                                <h2>❌ {len(ats_results['missing_skills'])}</h2>
                                <p>Missing Skills</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Matched Skills
                        if ats_results['matched_skills']:
                            st.subheader("✅ Your Matching Skills")
                            skills_html = " ".join([f'<span style="background-color: #e6ffed; color: #22863a; padding: 5px 10px; border-radius: 5px; margin: 5px; display: inline-block;">{skill.title()}</span>' for skill in ats_results['matched_skills'][:15]])
                            st.markdown(skills_html, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Missing Skills
                        if ats_results['missing_skills']:
                            st.subheader("❌ Skills to Add")
                            skills_html = " ".join([f'<span style="background-color: #fff5f5; color: #c53030; padding: 5px 10px; border-radius: 5px; margin: 5px; display: inline-block;">{skill.title()}</span>' for skill in ats_results['missing_skills']])
                            st.markdown(skills_html, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Tips
                        st.subheader("💡 Improvement Tips")
                        for i, tip in enumerate(ats_results['tips'], 1):
                            st.markdown(f'<div class="tip-box"><strong>{i}.</strong> {tip}</div>', unsafe_allow_html=True)
                
                # Optimized CV Tab
                cv_tab = tab2 if job_text else tab1
                with cv_tab:
                    st.header("📄 ATS-Optimized CV")
                    
                    with st.spinner("Generating your optimized CV..."):
                        cv_pdf = generate_optimized_cv(final_data, job_text)
                    
                    st.success("✅ CV generated successfully!")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.info("📥 Download your professionally formatted, ATS-optimized CV")
                    with col2:
                        st.download_button(
                            label="📥 Download CV",
                            data=cv_pdf,
                            file_name="optimized_cv.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    st.markdown("---")
                    
                    st.markdown("""
                    ### ✨ What's Included:
                    - Professional formatting optimized for ATS systems
                    - Clear section headers and organization
                    - Keyword-rich content based on your profile
                    - Clean, modern design
                    """)
                
                # Portfolio Tab
                portfolio_tab = tab3 if job_text else tab2
                with portfolio_tab:
                    st.header("🌐 Professional Portfolio Website")
                    
                    with st.spinner("Building your portfolio website..."):
                        portfolio_zip = generate_portfolio(final_data)
                    
                    st.success("✅ Portfolio generated successfully!")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.info("📦 Download your complete portfolio website (HTML + Tailwind CSS)")
                    with col2:
                        st.download_button(
                            label="📥 Download Portfolio",
                            data=portfolio_zip,
                            file_name="portfolio_website.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                    
                    st.markdown("---")
                    
                    st.markdown("""
                    ### 🎨 Portfolio Features:
                    - **Responsive Design**: Works perfectly on all devices
                    - **Modern UI**: Built with Tailwind CSS
                    - **Sections Included**:
                      - Hero section with your name
                      - About Me
                      - Skills showcase
                      - Experience timeline
                      - Contact information
                    
                    ### 🚀 Deployment Options (All FREE):
                    1. **GitHub Pages**: Upload to GitHub and enable Pages
                    2. **Netlify**: Drag & drop the folder
                    3. **Vercel**: Connect your GitHub repo
                    4. **Cloudflare Pages**: Simple drag & drop
                    """)
                
                # Skills Roadmap Tab (only if job description provided)
                if job_text:
                    with tab4:
                        st.header("📚 Personalized Learning Roadmap")
                        
                        if ats_results['missing_skills']:
                            roadmap_md = generate_skills_roadmap(ats_results['missing_skills'])
                            st.markdown(roadmap_md)
                            
                            # Download roadmap
                            st.download_button(
                                label="📥 Download Roadmap",
                                data=roadmap_md,
                                file_name="learning_roadmap.md",
                                mime="text/markdown"
                            )
                        else:
                            st.success("🎉 Great! Your skills align well with the job requirements!")
                            st.info("Keep learning and stay updated with industry trends.")
                
                # Extracted Data Tab
                data_tab = tab5 if job_text else tab3
                with data_tab:
                    st.header("📋 Extracted Information")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("👤 Personal Info")
                        st.write(f"**Name:** {final_data.get('name', 'N/A')}")
                        st.write(f"**Email:** {final_data.get('email', 'N/A')}")
                        st.write(f"**Phone:** {final_data.get('phone', 'N/A')}")
                    
                    with col2:
                        st.subheader("🎯 Skills Count")
                        st.metric("Total Skills", len(final_data.get('skills', [])))
                        st.metric("Experience Entries", len(final_data.get('experience', [])))
                        st.metric("Education Entries", len(final_data.get('education', [])))
                    
                    st.markdown("---")
                    
                    # Skills
                    if final_data.get('skills'):
                        st.subheader("💼 Extracted Skills")
                        skills_cols = st.columns(4)
                        for i, skill in enumerate(final_data['skills']):
                            with skills_cols[i % 4]:
                                st.markdown(f"✓ {skill}")
                    
                    st.markdown("---")
                    
                    # Experience
                    if final_data.get('experience'):
                        st.subheader("🏢 Experience")
                        for exp in final_data['experience']:
                            with st.expander(exp.get('title', 'Experience')):
                                st.write(exp.get('description', 'No description available'))
                    
                    st.markdown("---")
                    
                    # Education
                    if final_data.get('education'):
                        st.subheader("🎓 Education")
                        for edu in final_data['education']:
                            st.write(f"• {edu}")
        
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            st.info("Please check your inputs and try again.")

if __name__ == "__main__":
    main()
