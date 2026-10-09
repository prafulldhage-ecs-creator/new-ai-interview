# InterviewIQ - AI Placement Interview Simulator

> **A realistic, multi-turn AI technical & HR placement interview simulation platform engineered for engineering students preparing for internships and campus placements.**

Built with **Django**, **SQLite**, **Vanilla JavaScript**, and the **Web Speech API**, with support for modular LLM backends (OpenAI, Gemini, OpenAI-compatible APIs) alongside a fully deterministic, offline-capable **Demo Mode**.

---

## 🌟 Key Features

1. **Realistic Multi-Turn Interview Dialogue**
   - The AI interviewer listens, evaluates correctness, asks follow-up questions, and challenges shallow answers.
   - Preserves conversational context across questions.
   - Avoids repetitive questioning or revealing answers immediately upon a mistake.

2. **Multi-Domain Technical & HR Simulations**
   - Covers 13 specialized domains: Data Structures & Algorithms, DBMS & SQL, Operating Systems, Computer Networks, Object-Oriented Programming, Python, Java, JavaScript, React, C & C++, AI & ML, Software Engineering, and HR / Behavioral (STAR method).

3. **Dynamic & Adaptive Difficulty**
   - Select from Easy, Medium, Hard, or **Adaptive**.
   - In Adaptive mode, the system automatically dials difficulty up or down based on the candidate's real-time accuracy and depth.

4. **Speech-to-Text & Text-to-Speech (Web Speech API)**
   - Speak your answers naturally. View and edit your speech transcript in real-time before submission.
   - Text-to-Speech audio playback for interviewer questions with stop controls.

5. **Client-Side Presence Feedback (Webcam)**
   - Optional, client-side camera presence monitor.
   - **Strict Privacy Guarantee:** Video frames are analyzed locally in the browser canvas; no video or images are ever uploaded or stored.
   - Non-punitive and separate from technical competence scores.

6. **Structured Evaluation & Post-Interview Report**
   - Detailed per-question feedback: Classification, Correct Concepts, Missing Concepts, Analysis, Actionable Suggestions, and Exemplary Answers.
   - Communication transcript metrics: Word count, filler word ratio, and clarity levels.
   - Targeted knowledge gap analysis and personalized revision roadmap.

7. **Dual Operation Modes**
   - **Demo Mode (Default):** Deterministic, zero-cost, offline rule-based evaluation. Never fabricates AI evaluations.
   - **Real AI Mode:** Connects to OpenAI, Gemini, or custom OpenAI-compatible endpoints via environment variables.

---

## 📐 Scoring Rubric & Methodology

Every candidate answer is evaluated using a documented, objective 4-pillar rubric:

| Dimension | Weight | Description |
| :--- | :---: | :--- |
| **Technical Correctness** | **40%** | Accuracy of facts, algorithmic time/space complexities, mechanisms, and syntax principles. |
| **Conceptual Depth** | **25%** | Understanding of *why* things work under the hood, memory models, protocols, and architecture. |
| **Completeness** | **20%** | Addressing all parts of the question, handling edge cases, and avoiding omissions. |
| **Practical Reasoning** | **15%** | Mentioning real-world use cases, trade-offs, and design decisions. |

### Answer Classifications
- **Correct (88 - 100):** Comprehensive, accurate, structured response.
- **Mostly Correct (72 - 87):** Core premise is sound; minor omission or edge case missing.
- **Partially Correct (50 - 71):** Identified parts of the solution; missing critical mechanisms or trade-offs.
- **Incorrect (15 - 49):** Erroneous explanations or factual blunders.
- **Vague (35 - 55):** High-level buzzwords without substantive explanation.
- **Needs Clarification (40 - 60):** Fragmented or ambiguous line of thought.
- **Unable to Evaluate (0 - 15):** Candidate answered "I don't know", empty response, or gibberish.

*Note: Speech pace and filler words are evaluated strictly for communication coaching and are never conflated with technical competence.*

---

## 🛠️ Technology Stack

- **Backend:** Python 3.11+ / Django 5+ / 6+
- **Database:** SQLite (Django ORM)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Fetch API, Web Speech API)
- **AI Integrations:** OpenAI SDK / Google Gemini REST / Modular Extensibility

---

## 🚀 Quick Start (Windows)

The simplest way to run InterviewIQ on Windows is using the included `run.bat` script:

1. Double-click **`run.bat`** or run it from PowerShell:
   ```cmd
   .\run.bat
   ```
2. The script will automatically:
   - Verify Python installation.
   - Create a virtual environment (`venv`).
   - Install required dependencies.
   - Apply database migrations.
   - Launch the local development server at `http://127.0.0.1:8000/`.

---

## 💻 Manual Setup Instructions

### 1. Required Python Version
- **Python 3.11, 3.12, 3.13, or 3.14** (64-bit recommended).

### 2. Open in VS Code
```bash
cd ai-placement-interview-pro
code .
```

### 3. Create & Activate Virtual Environment
**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```
**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Default configuration uses **Demo Mode** (`AI_PROVIDER=demo`), requiring no API keys.

### 6. Apply Database Migrations
```bash
python manage.py makemigrations interviews
python manage.py migrate
```

### 7. (Optional) Create Superuser / Admin Account
```bash
python manage.py createsuperuser
```

### 8. Start the Development Server
```bash
python manage.py runserver 127.0.0.1:8000
```

### 9. Access the Website
Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

---

## 🤖 Configuring Real AI Mode

To enable live generative LLM evaluations:

### Option A: OpenAI (ChatGPT Models)
1. Open `.env`.
2. Configure:
   ```env
   AI_PROVIDER=openai
   AI_API_KEY=sk-your-openai-api-key-here
   AI_MODEL=gpt-4o-mini
   ```
3. Restart the Django server.

### Option B: Google Gemini
1. Open `.env`.
2. Configure:
   ```env
   AI_PROVIDER=gemini
   AI_API_KEY=your-gemini-api-key-here
   AI_MODEL=gemini-1.5-flash
   ```
3. Restart the Django server.

### Option C: Local LLMs / Ollama / Groq / OpenRouter
Any OpenAI-compatible API endpoint can be used:
```env
AI_PROVIDER=openai
AI_API_BASE=http://localhost:11434/v1
AI_API_KEY=ollama
AI_MODEL=llama3
```

---

## 🌐 Feature Matrix & Online Requirements

| Feature | Works Offline? | Works in Demo Mode? | Notes |
| :--- | :---: | :---: | :--- |
| **Placement Mock Interview** | ✅ Yes | ✅ Yes | Deterministic rule-based banks in demo mode. |
| **Text Answers** | ✅ Yes | ✅ Yes | Instant local processing. |
| **Webcam Presence Observer** | ✅ Yes | ✅ Yes | Uses browser Canvas / Shape Detection API. |
| **Speech-to-Text (STT)** | ⚠️ Browser Dependent | ✅ Yes | Chrome/Edge utilize Google speech services (requires internet). |
| **Text-to-Speech (TTS)** | ✅ Yes | ✅ Yes | Uses local browser synthesized voices. |
| **Real LLM Dynamic Follow-ups** | ❌ Needs Internet | ❌ Requires API Key | Requires OpenAI or Gemini credentials. |

---

## 🧪 Automated Testing

Run Django's built-in system verification:
```bash
python manage.py check
```

Execute all automated test suites:
```bash
python manage.py test
```

Python compilation check:
```bash
python -m compileall .
```

---

## 🔧 Troubleshooting Common Issues

1. **`python: command not found`:**
   Ensure Python is added to your Windows PATH during installation.
2. **`Script Execution Policy Error` in PowerShell:**
   Run: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.
3. **Microphone permission denied:**
   Click the camera/microphone icon in the browser address bar and select **Allow**. Note that speech recognition requires `localhost` or `https://`.
4. **AI provider timeout:**
   Check your internet connection and increase `AI_TIMEOUT_SECONDS=35` in `.env`. If the external provider fails, InterviewIQ automatically falls back to local evaluation without crashing.
