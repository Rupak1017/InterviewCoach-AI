"""Pydantic models used for structured AI outputs."""

from pydantic import BaseModel, Field


class QuestionOutput(BaseModel):
    question: str = Field(description="One interview question to ask the user.")
    topic: str = Field(description="The main topic tested by the question.")
    difficulty: str = Field(description="The question difficulty.")
    choices: list[str] = Field(description="Four multiple-choice answer options.")
    correct_answer: str = Field(description="The exact correct option from choices.")
    expected_points: list[str] = Field(
        description="Short points explaining why the correct option is right."
    )


class GradeOutput(BaseModel):
    score: int = Field(description="Answer score from 1 to 10.")
    strength: str = Field(description="One thing the user did well.")
    improvement: str = Field(description="One concrete way to improve.")
    feedback: str = Field(description="Short constructive feedback.")
    missing_points: list[str] = Field(description="Expected points the answer missed.")
    weak_area: str = Field(description="The main weak area to practice next.")
    correct_answer: str = Field(description="The correct MCQ answer.")
    sample_answer: str = Field(description="A short explanation of the correct answer.")
    next_topic_suggestion: str = Field(
        description="Suggested topic for the next adaptive interview question."
    )


class FinalReport(BaseModel):
    average_score: float = Field(description="Average interview score.")
    readiness_level: str = Field(description="Overall interview readiness verdict.")
    strong_areas: list[str] = Field(description="Topics or skills that looked strong.")
    weak_areas: list[str] = Field(description="Topics or skills that need practice.")
    recommended_topics: list[str] = Field(description="Study topics to review next.")
    practice_tasks: list[str] = Field(description="Three practical practice tasks.")
    final_message: str = Field(description="Friendly closing message.")
