import pytest

from neurosonic_ml.nlp.llm import LLMProvider, LocalFallbackProvider
from neurosonic_ml.nlp.parser import merge_llm_json, parse_text
from neurosonic_ml.rag.engine import NeuroGuide, TfidfEmbedder, VectorStore, load_chunks


def test_parse_exhausted_but_focus():
    r = parse_text("I feel mentally exhausted but I want to focus.")
    assert "exhausted" in r["emotions"] and r["intent"] == "focus"
    assert r["desired_transition"]["to"] == "focus" and r["state_estimate"]["arousal"] < 0.3


def test_parse_preferences_and_context():
    r = parse_text("stressed about my exam, I need to calm down. lofi piano please")
    assert r["intent"] == "calm" and {"lofi", "piano"} <= set(r["music_preferences"]) and "study" in r["context"]
    assert r["state_estimate"]["stress"] > 0.5


def test_parse_negation_and_empty():
    assert parse_text("I'm not calm at all")["state_estimate"]["arousal"] > 0.5
    empty = parse_text("hello there")
    assert empty["state_estimate"] is None and empty["confidence"] == 0.0


def test_llm_json_merge_is_validated():
    base = parse_text("tired")
    merged = merge_llm_json(base, 'sure: {"intent":"energize","state_estimate":{"valence":9,"arousal":0.8},"emotions":["sleepy"]}')
    assert merged["intent"] == "energize" and merged["state_estimate"]["valence"] == 1.0  # clipped
    assert merge_llm_json(base, "garbage") == base


def test_chunks_cover_all_documents_with_kinds():
    chunks = load_chunks()
    assert len(chunks) > 20 and {c.kind for c in chunks} == {"science", "system"}
    assert all(0 < len(c.text.split()) < 220 for c in chunks)


def test_retrieval_finds_relevant_document():
    store = VectorStore(load_chunks(), TfidfEmbedder())
    assert store.search("What does alpha activity represent?")[0][0].doc == "eeg-frequency-bands"
    assert store.search("what is the iso principle")[0][0].doc == "music-therapy-and-regulation"
    assert store.search("limitations individual variability noise")[0][0].doc == "limitations-of-eeg-emotion-inference"


def test_guide_separates_science_from_inference():
    g = NeuroGuide(LocalFallbackProvider())
    ctx = {"emotion": {"label": "Stressed", "valence": .2, "arousal": .8, "focus": .4, "stress": .8, "confidence": .6,
                       "feature_importance": [{"label": "Beta power", "direction": "raises", "most_affects": "arousal"}]}}
    out = g.ask("Why did the system classify my state as high arousal?", ctx)
    assert "Established science" in out["answer"] and "Model inference (this session)" in out["answer"]
    assert out["sources"] and out["provider"] == "local-extractive" and "medical" in out["disclaimer"].lower()


def test_guide_with_llm_provider_uses_sources():
    class Fake(LLMProvider):
        name = "fake"
        seen = ""

        def available(self):
            return True

        def complete(self, system, user, max_tokens=500, temperature=0.2):
            Fake.seen = user
            return "Established science: alpha ... [S1]"
    out = NeuroGuide(Fake()).ask("What does alpha activity represent?")
    assert out["provider"] == "fake" and "[S1]" in Fake.seen


def test_guide_unknown_topic_is_honest():
    out = NeuroGuide(LocalFallbackProvider()).ask("zzzz qqqq xxxx")
    assert "could not find" in out["answer"].lower()


@pytest.mark.parametrize("q", ["How does EEG-based emotion recognition work?", "What are the limitations of EEG emotion inference?"])
def test_guide_answers_core_questions(q):
    assert NeuroGuide(LocalFallbackProvider()).ask(q)["sources"]
