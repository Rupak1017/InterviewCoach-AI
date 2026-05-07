# InterviewCoach AI

InterviewCoach AI is a polished Streamlit mini app for practicing job interviews. Pick a role, answer one question at a time, get scored feedback, and finish with a short readiness report.

Supported roles:
- Frontend Developer
- Backend Developer
- Data Analyst
- AI Engineer Intern

## What The AI Parts Do

LangChain handles the Gemini prompt calls and structured Pydantic outputs for question generation, answer grading, and final reports.

LangGraph controls the interview flow. The app runs one small graph to ask a question, pauses for the user's answer, then runs another graph to grade the answer and either ask the next question or create the final report.

Tools are simple Python functions for choosing topics, calculating averages, finding weak areas, creating study plans, and saving scores.

Middleware keeps the app friendly and reliable by blocking too-short answers, clamping scores to 1-10, shortening feedback, and guarding against rude or dishonest advice.

JSON storage is used because this is a beginner-friendly portfolio project. There is no SQLite, no database server, and no external storage service.

## Windows + VS Code Setup

1. Open the project folder in VS Code.
2. Open Terminal -> New Terminal.
3. Run:

```bat
setup.bat
```

4. Open the `.env` file.
5. Add your Gemini API key:

```env
GEMINI_API_KEY=your_real_key_here
```

6. Run:

```bat
run.bat
```

7. The app should open in your browser.

## Gemini API Key

The app supports either variable name:

```env
GEMINI_API_KEY=your_key_here
```

or:

```env
GOOGLE_API_KEY=your_key_here
```

The default model is:

```env
MODEL_NAME=gemini-1.5-flash
```

You can change `MODEL_NAME` in `.env` if you want to use a different Gemini model.

## Mock Mode

If no Gemini API key is found, the app does not crash. It runs in mock mode with deterministic sample questions, useful grading, and a final report. The Streamlit UI will show:

```text
Running in mock mode because no Gemini API key was found.
```

## Manual Windows Setup

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Then add your Gemini key to `.env` when you want real AI responses.

## Example Flow

1. Choose `AI Engineer Intern`.
2. Choose `Easy`, `Medium`, or `Hard`.
3. Choose 3, 5, or 10 questions.
4. Click `Start Interview`.
5. Answer the question in the chat box.
6. Review your score, strength, improvement, missing points, and sample answer.
7. Continue until the final report appears.

## Data Storage

Sessions are saved in:

```text
data/interview_sessions.json
```

If the file is missing, the app creates it. If the file is corrupted, the app backs it up as:

```text
data/interview_sessions_backup.json
```

and starts with a clean JSON file.

## Project Structure

```text
app.py
graph.py
chains.py
tools.py
storage.py
middleware.py
prompts.py
models.py
requirements.txt
.env.example
.gitignore
setup.bat
run.bat
README.md
data/
  .gitkeep
```

## Future Improvements

- Add exportable PDF reports.
- Add role-specific question packs.
- Add optional resume-based question generation.
- Add charts for score trends over time.
- Add more granular difficulty adaptation.
