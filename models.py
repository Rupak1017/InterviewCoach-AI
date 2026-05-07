"""Pydantic models used for structured AI outputs."""

from pydantic import BaseModel, Field


class PrepSource(BaseModel):
    title: str = Field(description="Source title.")
    url: str = Field(description="Clickable source URL.")
    snippet: str = Field(description="Short source summary or search snippet.")


class QuickPrep(BaseModel):
    overview: str = Field(description="Two to four sentence topic overview.")
    key_points: list[str] = Field(description="Two short points to remember.")
    common_mistake: str = Field(description="One common mistake to avoid.")
    sources: list[PrepSource] = Field(description="Useful study sources.")


class QuestionOutput(BaseModel):
    question: str = Field(description="One interview question to ask the user.")
    topic: str = Field(description="The main topic tested by the question.")
    difficulty: str = Field(description="The question difficulty.")
    choices: list[str] = Field(description="Exactly three answer options.")
    correct_answer: str = Field(description="The exact correct option from choices.")
    expected_points: list[str] = Field(
        description="Short points that explain why the correct answer is right."
    )


class GradeOutput(BaseModel):
    score: int = Field(description="Answer score from 1 to 10.")
    strength: str = Field(description="One thing the user did well.")
    improvement: str = Field(description="One concrete way to improve.")
    feedback: str = Field(description="Short constructive feedback.")
    missing_points: list[str] = Field(description="Expected points the answer missed.")
    weak_area: str = Field(description="The main weak area to practice next.")
    correct_answer: str = Field(description="The correct option.")
    sample_answer: str = Field(description="A better sample answer.")
    study_next: list[str] = Field(description="Short topics or actions to study next.")
    recommended_links: list[PrepSource] = Field(description="Useful study links.")


class FinalReport(BaseModel):
    average_score: float = Field(description="Average interview score.")
    readiness_level: str = Field(description="Overall interview readiness verdict.")
    strong_areas: list[str] = Field(description="Topics or skills that looked strong.")
    weak_areas: list[str] = Field(description="Topics or skills that need practice.")
    recommended_topics: list[str] = Field(description="Study topics to review next.")
    useful_sources: list[PrepSource] = Field(description="Useful sources from the session.")
    practice_tasks: list[str] = Field(description="Three practical practice tasks.")
    final_message: str = Field(description="Friendly closing message.")
