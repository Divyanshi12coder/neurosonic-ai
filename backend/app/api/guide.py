from fastapi import APIRouter

from ..schemas import ChatIn, ChatOut, TextAnalysis, TextIn
from ..services import engine

router = APIRouter(tags=["guide"])

SUGGESTIONS = [
    "Why did the system classify my state as high arousal?",
    "What does alpha activity represent?",
    "Why did you recommend this type of music?",
    "How does EEG-based emotion recognition work?",
    "What are the limitations of EEG emotion inference?",
    "What is the iso principle in music therapy?",
]


@router.post("/guide/chat", response_model=ChatOut)
def chat(body: ChatIn):
    ctx = body.context.model_dump() if body.context else None
    return engine.guide().ask(body.message, ctx)


@router.get("/guide/suggestions", response_model=list[str])
def suggestions():
    return SUGGESTIONS


@router.post("/nlp/parse", response_model=TextAnalysis)
def parse(body: TextIn):
    return engine.analyze_text(body.text)
