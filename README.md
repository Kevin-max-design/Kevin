# 🚀 AI Job & Internship Application Agent

An intelligent, production-ready job application automation system with semantic matching, resume tailoring, and human-in-the-loop approval workflow.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![React](https://img.shields.io/badge/React-18+-61dafb.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🔍 Smart Job Discovery
- Multi-platform scraping (LinkedIn, Indeed, Glassdoor, AngelList, Naukri)
- Configurable search filters (location, job type, work mode)
- Duplicate detection and deduplication

### 🎯 Semantic Matching
- Vector embedding-based similarity matching
- Skill gap analysis
- Multi-variant resume support
- Automatic best-match resume selection

### 📄 Resume Intelligence
- PDF/DOCX resume parsing
- Skill extraction and categorization
- Experience timeline parsing
- ATS-optimized resume generation

### ✅ Human-in-the-Loop Workflow
- Approval queue with match scores
- Quick approve/reject actions
- Cover letter preview before submission
- Activity logging and audit trail

### 🤖 Intelligent Automation
- Playwright-based browser automation
- Stealth mode (anti-bot detection)
- Human-like typing and interaction
- Screenshot capture for verification

### 🎤 Interview Preparation
- Topic prediction from job descriptions
- Technical question generation
- HR/behavioral question preparation
- Day-by-day study plans

### 📊 Analytics Dashboard
- Application statistics
- Interview/offer rate tracking
- Platform breakdown
- CSV/JSON/Google Sheets export

## 🏗️ Architecture

```
job-application-agent/
├── src/
│   ├── api/              # FastAPI backend
│   ├── database/         # SQLAlchemy models
│   ├── scrapers/         # Job platform scrapers
│   ├── intelligence/     # Resume/JD parsing & matching
│   ├── generator/        # Resume & cover letter generation
│   ├── applicator/       # Application automation
│   ├── interview/        # Interview prep module
│   ├── tracking/         # Analytics & export
│   └── llm/              # LLM integration (Ollama)
├── dashboard/            # React frontend
├── config/               # Configuration files
├── data/                 # User data & database
└── tests/                # Test suites
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+ (for dashboard)
- Ollama (optional, for LLM features)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/job-application-agent.git
cd job-application-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Install dashboard dependencies
cd dashboard
npm install
cd ..
```

### Configuration

1. Copy the example configuration:
```bash
cp config/config.example.yaml config/config.yaml
```

2. Edit your profile:
```bash
cp data/profile.example.yaml data/profile.yaml
```

3. Add your details to `data/profile.yaml`:
```yaml
personal:
  name: "Your Name"
  email: "your.email@example.com"
  phone: "+1-234-567-8900"
  linkedin: "https://linkedin.com/in/yourprofile"

skills:
  programming: ["Python", "JavaScript", "SQL"]
  ml_ai: ["Machine Learning", "Deep Learning", "NLP"]
  tools: ["Git", "Docker", "AWS"]

experience:
  total_years: 3
  current_role: "Data Scientist"
```

### Running

```bash
# Terminal 1: Start API server
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Start dashboard
cd dashboard
npm run dev
```

Open http://localhost:5173 to access the dashboard.

## 📖 Usage

### 1. Scrape Jobs
Click "🔍 Scrape Jobs" to fetch new job listings from configured platforms.

### 2. Run Matching
Click "🎯 Run Matching" to score jobs against your profile using semantic similarity.

### 3. Review & Approve
Go to the **Approvals** tab to review matched jobs. Click ✓ to approve or ✕ to reject.

### 4. Apply
Click "📤 Apply Now" on approved jobs. The system will:
- Generate a tailored cover letter
- Fill application forms automatically
- Take screenshots for verification

### 5. Track Progress
Monitor your applications in the **Jobs** tab with status tracking.

### 6. Prepare for Interviews
Click "🎯 Interview Prep" on any job to generate customized preparation materials.

## 🔧 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/stats` | GET | Application statistics |
| `GET /api/jobs` | GET | List jobs (with filters) |
| `GET /api/jobs/pending` | GET | Jobs awaiting approval |
| `POST /api/jobs/{id}/approve` | POST | Approve job |
| `POST /api/jobs/{id}/reject` | POST | Reject job |
| `POST /api/jobs/{id}/apply` | POST | Apply to job |
| `GET /api/jobs/{id}/cover-letter` | GET | Preview cover letter |
| `POST /api/jobs/{id}/interview-prep` | POST | Generate interview prep |
| `POST /api/scrape` | POST | Trigger scraping |
| `POST /api/match` | POST | Run matching |
| `GET /api/activity` | GET | Activity feed |
| `GET /api/export` | GET | Export data |

## 🎨 Dashboard Screenshots

The dashboard features a modern dark theme with:
- Sidebar navigation
- Stats overview cards
- Job listings with match scores
- Approval queue with quick actions
- Activity timeline
- Circular score visualizations

## ⚙️ Configuration Options

### `config/config.yaml`

```yaml
llm:
  model: "llama2"
  temperature: 0.7

automation:
  headless: false
  screenshot_dir: "data/screenshots"

application:
  daily_limit: 20
  min_match_score: 60.0

platforms:
  linkedin:
    enabled: true
  indeed:
    enabled: true
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

## 🐳 Docker (Coming Soon)

```bash
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

This tool is for educational and personal use. Always respect platform terms of service and rate limits. The authors are not responsible for any misuse.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) for local LLM inference
- [Playwright](https://playwright.dev) for browser automation
- [Sentence Transformers](https://sbert.net) for semantic matching
- [FastAPI](https://fastapi.tiangolo.com) for the API framework
- [React](https://react.dev) for the dashboard
