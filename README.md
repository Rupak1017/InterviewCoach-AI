# InterviewCoach AI

InterviewCoach AI is a Streamlit mini app with one simple flow: **Guided Practice Mode**.

The user selects a role, enters a topic, chooses difficulty and question count, then practices one 3-option MCQ interview question at a time. The app combines quick prep, interview questions, answer grading, weak-area tracking, useful study links, and a final report.

Supported roles:
- Frontend Developer
- Backend Developer
- Data Analyst
- AI Engineer

Simple project explanation:

> InterviewCoach AI uses Gemini to generate and grade interview questions, LangGraph to control the guided practice flow, Tavily as a tool to fetch relevant study links, and JSON storage to save sessions locally.

## Guided Practice Mode

1. Choose a role.
2. Enter a topic, such as `AWS Bedrock`, `LangChain`, `React Hooks`, `LangGraph state`, `RAG`, `SQL joins`, or `Python decorators`.
3. Choose `Easy`, `Medium`, or `Hard`.
4. Choose 3, 5, or 10 questions.
5. Click `Start Guided Practice`.
6. Review the Quick Prep card.
7. Select one of three answer options.
8. Get a score, feedback, study-next items, useful links, and the correct-answer explanation.
9. Continue until the final report appears.

When the app first opens, a guided onboarding tour highlights one section at a time. Use `Next`, `Back`, `Skip`, or `Finish` to move through it.

## What LangChain Does

LangChain connects the app to Gemini through `langchain-google-genai`.

Gemini is used for:
- Quick prep generation
- Interview question generation
- Answer grading
- Final report generation

The app uses Pydantic structured outputs so each response is predictable and easy to render in Streamlit.

## What LangGraph Does

LangGraph controls the guided practice workflow.

Question flow:

```text
START -> prepare_context_node -> generate_question_node -> END
```

Answer flow:

```text
START -> grade_answer_node -> route_after_grading
```

If more questions remain, the graph prepares context and asks the next question. If the practice is complete, the graph generates the final report.

## What Tools Do

`tools.py` contains small, easy-to-explain helpers:
- Choose the next topic
- Search study sources with Tavily
- Save answers to JSON
- Calculate average score
- Track weak areas
- Save the final session locally

## How Tavily Is Used

Tavily is the only external web-fetching tool.

The app uses Tavily only to fetch relevant study links and short snippets. It does not scrape full websites, copy long website content, or build a complicated research system.

If `TAVILY_API_KEY` is missing, the app still runs and uses mock study links.

## JSON Storage

The app uses local JSON storage only.

Sessions are saved in:

```text
data/interview_sessions.json
```

There is no SQL, SQLite, PostgreSQL database, or database server.

If the JSON file is missing, the app creates it. If the JSON file is corrupted, the app backs it up as:

```text
data/interview_sessions_backup.json
```

and starts with a clean JSON file.

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

6. Optionally add your Tavily API key:

```env
TAVILY_API_KEY=your_tavily_key_here
```

7. Run:

```bat
run.bat
```

8. The app should open in your browser.

## API Keys

Gemini can use either variable name:

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

Tavily is optional:

```env
TAVILY_API_KEY=your_tavily_key_here
```

## Mock Mode

If no Gemini key is found, the app shows:

```text
Running in mock mode because no Gemini API key was found.
```

If no Tavily key is found, the app shows:

```text
Using mock study links because TAVILY_API_KEY was not found.
```

Both mock modes are safe. The app still runs without crashing.

## Manual Windows Setup

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

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

- Add exportable reports.
- Add more role-specific question packs.
- Add optional resume-based question generation.
- Add charts for score trends over time.
