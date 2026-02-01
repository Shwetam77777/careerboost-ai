import streamlit as st
from utils import (
    parse_cv,
    parse_linkedin,
    analyze_ats,
    generate_optimized_cv,
    generate_portfolio,
    generate_skills_roadmap,
    parse_pdf,
    parse_txt,
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CareerBoost AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': 'CareerBoost AI — Free ATS optimization & portfolio generator.',
    }
)

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
  /* hide default streamlit chrome */
  #MainMenu, footer, .reportview-container .main .block-container > div:first-child { display:none !important; }

  /* ── gradient header ── */
  .cb-header {
      text-align:center;
      padding:1.6rem 0 .4rem;
  }
  .cb-header h1 {
      font-size:2.8rem;
      font-weight:800;
      background:linear-gradient(90deg,#e94560,#c23152,#764ba2);
      -webkit-background-clip:text;
      -webkit-text-fill-color:transparent;
      margin:0; line-height:1.15;
  }
  .cb-header p {
      color:#7a7f8e; font-size:.95rem; margin-top:.35rem;
  }

  /* ── sidebar tweaks ── */
  .stSidebar { background:#13151f !important; }
  .stSidebar .stMarkdown h3 { color:#fff !important; }

  /* ── score ring ── */
  .score-ring {
      width:140px; height:140px; margin:0 auto;
      border-radius:50%;
      display:flex; align-items:center; justify-content:center;
      flex-direction:column;
      font-family:'Segoe UI',sans-serif;
  }
  .score-ring .num { font-size:2.2rem; font-weight:800; color:#fff; }
  .score-ring .lbl { font-size:.72rem; color:#aaa; text-transform:uppercase; letter-spacing:1px; }

  /* ── tag pills ── */
  .pill {
      display:inline-block; padding:4px 12px; border-radius:20px;
      font-size:.78rem; font-weight:600; margin:3px;
  }
  .pill-green  { background:#1a3a2a; color:#4ade80; }
  .pill-red    { background:#3a1a1f; color:#f87171; }

  /* ── tip card ── */
  .tip-card {
      background:#161923; border-left:3px solid #e94560;
      border-radius:6px; padding:.85rem 1rem;
      margin:.45rem 0; font-size:.88rem; color:#c8cad0;
  }
  .tip-card strong { color:#fff; }

  /* ── download strip ── */
  .dl-strip {
      background:#1a1d27; border:1px solid #2a2d38;
      border-radius:10px; padding:1rem 1.3rem;
      display:flex; align-items:center; gap:1rem;
      margin-top:1rem;
  }
  .dl-strip .dl-icon { font-size:1.6rem; }
  .dl-strip .dl-text { font-size:.82rem; color:#7a7f8e; }
  .dl-strip .dl-text strong { color:#e2e4e9; font-size:.9rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _fetch_job_from_url(url: str) -> str:
    """Try to pull job description text from a URL."""
    import requests
    from bs4 import BeautifulSoup
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # strip scripts/styles
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        # return a reasonable chunk
        return '\n'.join(text.split('\n')[:200])
    except Exception as e:
        raise Exception(f"Could not fetch URL: {e}")


def _score_color(score: int) -> str:
    if score >= 75: return "linear-gradient(135deg,#16a34a,#22c55e)"
    if score >= 50: return "linear-gradient(135deg,#ca8a04,#eab308)"
    return "linear-gradient(135deg,#dc2626,#ef4444)"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    # ── Header ──
    st.markdown('<div class="cb-header"><h1>🚀 CareerBoost AI</h1>'
                '<p>ATS optimization • CV generation • Portfolio builder • Skills roadmap</p></div>',
                unsafe_allow_html=True)

    # ─── SIDEBAR ───────────────────────────────
    with st.sidebar:
        st.markdown("### 📄 Your Documents")
        cv_file = st.file_uploader(
            "Upload CV / Resume",
            type=['pdf', 'docx', 'doc', 'txt'],
            help="PDF, DOCX or TXT"
        )

        linkedin_url = st.text_input(
            "LinkedIn URL (optional)",
            placeholder="https://linkedin.com/in/yourname",
            help="Public profile only"
        )

        st.markdown("---")
        st.markdown("### 🎯 Job Description (optional)")

        job_mode = st.radio("Input method", ["Paste text", "Upload PDF", "Paste URL"], label_visibility="collapsed")

        job_text_input = ""
        job_file_input = None
        job_url_input  = ""

        if job_mode == "Paste text":
            job_text_input = st.text_area("Job description", height=180, placeholder="Paste here…", label_visibility="collapsed")
        elif job_mode == "Upload PDF":
            job_file_input = st.file_uploader("Job desc PDF", type=['pdf', 'txt'], key="job_pdf", label_visibility="collapsed")
        else:
            job_url_input = st.text_input("Job posting URL", placeholder="https://…", label_visibility="collapsed")

        st.markdown("---")
        go = st.button("🚀  Analyze & Generate", type="primary", use_container_width=True)

    # ─── WELCOME STATE ────────────────────────
    if not go:
        c1, c2, c3 = st.columns(3)
        for col, title, icon, desc in [
            (c1, "ATS Scoring", "📊", "Keyword-match score vs any job description. Pinpoint exactly what's missing."),
            (c2, "CV Generation", "📄", "Download a clean, ATS-friendly PDF tailored to the role."),
            (c3, "Portfolio Site", "🌐", "A responsive, deployable HTML portfolio — no coding needed."),
        ]:
            with col:
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid #2a2d38;border-radius:12px;padding:1.6rem 1.2rem;height:100%;">
                  <div style="font-size:2rem;margin-bottom:.5rem;">{icon}</div>
                  <h4 style="color:#fff;margin-bottom:.4rem;">{title}</h4>
                  <p style="color:#7a7f8e;font-size:.82rem;line-height:1.5;">{desc}</p>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        st.info("👈  Upload your CV (and optionally a job description) in the sidebar, then hit **Analyze & Generate**.")
        return

    # ─── VALIDATION ───────────────────────────
    if not cv_file and not linkedin_url:
        st.error("⚠️ Please upload a CV **or** provide a LinkedIn URL.")
        return

    # ─── PROCESSING ───────────────────────────
    cv_data = None
    job_text = None

    with st.spinner("Parsing your documents…"):
        # --- CV ---
        if cv_file:
            try:
                cv_data = parse_cv(cv_file)
            except Exception as e:
                st.error(f"CV parse failed: {e}")
                return

        # --- LinkedIn ---
        if linkedin_url:
            try:
                li_data = parse_linkedin(linkedin_url)
                if cv_data:
                    # merge skills
                    cv_data['skills'] = list(dict.fromkeys(cv_data['skills'] + li_data.get('skills', [])))
                else:
                    cv_data = li_data
                st.info("LinkedIn data merged. (LinkedIn limits public scraping — CV upload gives richer results.)")
            except Exception as e:
                st.warning(str(e))

        if not cv_data:
            st.error("No usable data extracted. Please upload your CV.")
            return

        # --- Job description ---
        if job_text_input.strip():
            job_text = job_text_input.strip()
        elif job_file_input:
            try:
                if job_file_input.name.endswith('.pdf'):
                    job_text = parse_pdf(job_file_input)
                else:
                    job_text = parse_txt(job_file_input)
            except Exception as e:
                st.error(f"Job PDF parse failed: {e}")
                return
        elif job_url_input.strip():
            try:
                job_text = _fetch_job_from_url(job_url_input.strip())
            except Exception as e:
                st.error(str(e))
                return

    # ─── BUILD TABS ───────────────────────────
    ats_results = None
    if job_text:
        with st.spinner("Running ATS analysis…"):
            ats_results = analyze_ats(cv_data, job_text)

    # determine tab set
    if ats_results:
        tabs = st.tabs(["📊 ATS Analysis", "📄 Optimized CV", "🌐 Portfolio", "📚 Roadmap", "📋 Parsed Data"])
        t_ats, t_cv, t_port, t_road, t_data = tabs
    else:
        tabs = st.tabs(["📄 Optimized CV", "🌐 Portfolio", "📋 Parsed Data"])
        t_cv, t_port, t_data = tabs
        t_ats = t_road = None

    # ═══════════════════════════════════════════
    # TAB 1 — ATS ANALYSIS
    # ═══════════════════════════════════════════
    if t_ats and ats_results:
        with t_ats:
            score = ats_results['score']
            matched = ats_results['matched_skills']
            missing = ats_results['missing_skills']
            tips    = ats_results['tips']

            # score ring + 2 counters
            c1, c2, c3 = st.columns([1.2, 1, 1])
            with c1:
                st.markdown(f"""
                <div class="score-ring" style="background:{_score_color(score)};">
                  <div class="num">{score}%</div>
                  <div class="lbl">ATS Score</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.metric("✅ Matched", len(matched), help="Keywords found in your CV")
            with c3:
                st.metric("❌ Missing", len(missing), help="Keywords absent from your CV")

            st.markdown("---")

            # matched pills
            if matched:
                st.markdown("**Matched Skills**")
                st.markdown(" ".join(f'<span class="pill pill-green">{s.title()}</span>' for s in matched), unsafe_allow_html=True)
                st.markdown("")

            # missing pills
            if missing:
                st.markdown("**Skills to Add**")
                st.markdown(" ".join(f'<span class="pill pill-red">{s.title()}</span>' for s in missing), unsafe_allow_html=True)
                st.markdown("")

            st.markdown("---")

            # tips
            st.markdown("### 💡 Improvement Tips")
            for i, tip in enumerate(tips, 1):
                st.markdown(f'<div class="tip-card"><strong>{i}.</strong> {tip}</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # TAB 2 — OPTIMIZED CV
    # ═══════════════════════════════════════════
    with t_cv:
        with st.spinner("Generating ATS-optimized CV…"):
            cv_pdf = generate_optimized_cv(cv_data, job_text)

        st.markdown("""
        <div class="dl-strip">
          <div class="dl-icon">📄</div>
          <div class="dl-text">
            <strong>Optimized CV Ready</strong><br/>
            Professional layout, keyword-rich, ATS-friendly PDF.
          </div>
        </div>""", unsafe_allow_html=True)
        st.markdown("")
        st.download_button(
            "⬇️  Download CV (PDF)",
            data=cv_pdf,
            file_name="optimized_cv.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.markdown("---")
        st.markdown("""
        **What's included in the generated CV:**
        - Clean two-colour header with contact info
        - Professional Summary auto-generated from your skills
        - Skills section (up to 16 keywords)
        - Experience & Education pulled from your upload
        - Consistent typography optimised for ATS parsers
        """)

    # ═══════════════════════════════════════════
    # TAB 3 — PORTFOLIO
    # ═══════════════════════════════════════════
    with t_port:
        with st.spinner("Building your portfolio…"):
            port_zip = generate_portfolio(cv_data)

        st.markdown("""
        <div class="dl-strip">
          <div class="dl-icon">🌐</div>
          <div class="dl-text">
            <strong>Portfolio Website Ready</strong><br/>
            Single-file HTML + CSS. Deploy anywhere for free.
          </div>
        </div>""", unsafe_allow_html=True)
        st.markdown("")
        st.download_button(
            "⬇️  Download Portfolio (ZIP)",
            data=port_zip,
            file_name="portfolio.zip",
            mime="application/zip",
            use_container_width=True,
        )

        st.markdown("---")
        st.markdown("""
        **Sections included:** Hero · About · Skills Grid · Experience Timeline · Education · Contact

        **Free deployment options:**
        1. **GitHub Pages** — push `index.html` to a repo, enable Pages → live URL
        2. **Netlify** — drag & drop the folder on netlify.app
        3. **Vercel** — connect your GitHub repo in one click
        4. **Cloudflare Pages** — drag & drop, instant global CDN
        """)

    # ═══════════════════════════════════════════
    # TAB 4 — ROADMAP
    # ═══════════════════════════════════════════
    if t_road and ats_results:
        with t_road:
            missing = ats_results['missing_skills']
            if missing:
                with st.spinner("Building roadmap…"):
                    roadmap_md = generate_skills_roadmap(missing)
                st.markdown(roadmap_md)
                st.markdown("---")
                st.download_button(
                    "⬇️  Download Roadmap (Markdown)",
                    data=roadmap_md,
                    file_name="skills_roadmap.md",
                    mime="text/markdown",
                )
            else:
                st.success("🎉 Your skills are a strong match — no gaps detected!")

    # ═══════════════════════════════════════════
    # TAB 5 — PARSED DATA
    # ═══════════════════════════════════════════
    with t_data:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 👤 Profile")
            st.write(f"**Name:** {cv_data.get('name','—')}")
            st.write(f"**Email:** {cv_data.get('email','—')}")
            st.write(f"**Phone:** {cv_data.get('phone','—')}")
        with c2:
            st.markdown("#### 📊 Counts")
            st.metric("Skills", len(cv_data.get('skills', [])))
            st.metric("Experience entries", len(cv_data.get('experience', [])))
            st.metric("Education entries", len(cv_data.get('education', [])))

        st.markdown("---")

        # skills
        if cv_data.get('skills'):
            st.markdown("#### 💼 Detected Skills")
            cols = st.columns(5)
            for i, s in enumerate(cv_data['skills']):
                cols[i % 5].markdown(f"✓ {s}")

        st.markdown("---")

        # experience
        if cv_data.get('experience'):
            st.markdown("#### 🏢 Experience")
            for exp in cv_data['experience']:
                with st.expander(exp.get('title', 'Entry'), expanded=False):
                    st.write(exp.get('description', 'No additional detail.'))

        st.markdown("---")

        # education
        if cv_data.get('education'):
            st.markdown("#### 🎓 Education")
            for e in cv_data['education']:
                st.write(f"• {e}")


if __name__ == "__main__":
    main()
