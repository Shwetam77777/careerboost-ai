# 🚀 CareerBoost AI

An AI-powered career optimization platform that helps you create ATS-optimized CVs, professional portfolio websites, and personalized learning roadmaps.

## ✨ Features

- **CV Analysis**: Upload your CV (PDF/DOC/TXT) and get detailed insights
- **LinkedIn Integration**: Parse public LinkedIn profiles
- **ATS Scoring**: Get 0-100% compatibility score with job descriptions
- **Skill Gap Analysis**: Identify missing skills and get learning recommendations
- **CV Generation**: Create professionally formatted, ATS-optimized CVs
- **Portfolio Generator**: Build beautiful, responsive portfolio websites
- **Learning Roadmap**: Get personalized skill development plans

## 🚀 Quick Start

### Local Development

1. Clone the repository
```bash
git clone <your-repo-url>
cd careerboost-ai
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the app
```bash
streamlit run app.py
```

### Deploy to Hugging Face Spaces

1. Create a new Space on [Hugging Face](https://huggingface.co/spaces)
2. Select "Streamlit" as the SDK
3. Upload all files (app.py, utils.py, requirements.txt)
4. Your app will be live in minutes!

## 📁 Project Structure
```
careerboost-ai/
├── app.py              # Main Streamlit application
├── utils.py            # Utility functions (parsing, generation)
├── requirements.txt    # Python dependencies
└── README.md          # Documentation
```

## 💡 How to Use

1. **Upload Your CV**: Drag and drop your CV (PDF, DOC, DOCX, or TXT)
2. **Add LinkedIn (Optional)**: Paste your public LinkedIn profile URL
3. **Job Description (Optional)**: Add a job description for ATS analysis
4. **Click Analyze**: Get your results instantly!

## 🎯 Use Cases

- Job seekers optimizing their CVs
- Career changers identifying skill gaps
- Students creating professional portfolios
- Professionals tracking career development

## 🔒 Privacy

- All processing happens in-memory
- No data is stored or shared
- Your documents are secure

## 📝 License

MIT License - feel free to use and modify!

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## ⚠️ Note

LinkedIn scraping is limited due to platform restrictions. For best results, upload your CV directly.
