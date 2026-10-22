"""Lightweight custom RAG: ingestion -> chunking -> embeddings -> vector search -> grounded answer.

Embeddings are behind an interface. Default `TfidfEmbedder` is fully local (scikit-learn); an optional
`SentenceTransformerEmbedder` is used when EMBEDDING_PROVIDER=sentence-transformers and the package is installed.
The assistant keeps *established science* (retrieved documents) separate from *model inference* (this session).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..constants import DISCLAIMER
from ..nlp.llm import LLMError, LLMProvider

KB_DIR = Path(__file__).parent / "knowledge"
_STOP = {"what", "does", "why", "how", "the", "did", "you", "and", "with", "this", "that", "are", "for", "can", "which", "represent", "activity", "mean"}
SYSTEM_DOC = "neurosonic-system"


@dataclass
class Chunk:
    id: str
    doc: str
    title: str
    heading: str
    text: str
    kind: str  # "science" | "system"


def load_chunks(kb_dir: Path = KB_DIR, max_words: int = 110, overlap: int = 20) -> list[Chunk]:
    """Heading-aware chunking: split on markdown headings, then pack sentences up to `max_words` with overlap."""
    chunks: list[Chunk] = []
    for fp in sorted(kb_dir.glob("*.md")):
        raw = fp.read_text(encoding="utf-8")
        title = (re.match(r"#\s+(.+)", raw) or [None, fp.stem])[1]
        for sec in re.split(r"\n(?=##\s)", raw):
            m = re.match(r"##\s+(.+)", sec)
            heading = m.group(1).strip() if m else "Overview"
            body = re.sub(r"^#{1,3}\s+.*\n?", "", sec, count=1).strip()
            if not body:
                continue
            sents = [s.strip().lstrip("-* ").strip() for s in re.split(r"(?<=[.!?])\s+|\n(?=[-*] )", body)]
            sents = [s if s[-1:] in ".!?:" else s + "." for s in sents if s]
            cur: list[str] = []
            n = 0
            for s in sents:
                w = len(s.split())
                if cur and n + w > max_words:
                    chunks.append(Chunk(f"{fp.stem}#{len(chunks)}", fp.stem, title, heading, " ".join(cur), "system" if fp.stem == SYSTEM_DOC else "science"))
                    tail = " ".join(cur).split()[-overlap:]
                    cur, n = [" ".join(tail)], len(tail)
                cur.append(s)
                n += w
            if cur:
                chunks.append(Chunk(f"{fp.stem}#{len(chunks)}", fp.stem, title, heading, " ".join(cur), "system" if fp.stem == SYSTEM_DOC else "science"))
    return chunks


class EmbeddingProvider(ABC):
    name: str

    @abstractmethod
    def fit(self, texts: list[str]) -> None: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray: ...  # L2-normalised rows


class TfidfEmbedder(EmbeddingProvider):
    name = "local-tfidf"

    def __init__(self):
        self.v = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1)

    def fit(self, texts):
        self.v.fit(texts)

    def embed(self, texts):
        return self.v.transform(texts).toarray()  # rows are L2-normalised by TfidfVectorizer


class SentenceTransformerEmbedder(EmbeddingProvider):
    name = "sentence-transformers"

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # optional dependency
        self.m = SentenceTransformer(model)

    def fit(self, texts):
        pass

    def embed(self, texts):
        return np.asarray(self.m.encode(texts, normalize_embeddings=True))


def get_embedder(name: str = "local-tfidf") -> EmbeddingProvider:
    if name == "sentence-transformers":
        try:
            return SentenceTransformerEmbedder()
        except Exception:  # noqa: BLE001 - package missing or model download failed
            pass
    return TfidfEmbedder()


class VectorStore:
    def __init__(self, chunks: list[Chunk], embedder: EmbeddingProvider):
        self.chunks, self.embedder = chunks, embedder
        embedder.fit([c.text for c in chunks])
        # headings are repeated so a section titled "Alpha (8–13 Hz)" outranks passing mentions of alpha elsewhere
        self.matrix = embedder.embed([f"{c.heading}. {c.heading}. {c.title}. {c.text}" for c in chunks])

    def search(self, query: str, k: int = 4, min_score: float = 0.05) -> list[tuple[Chunk, float]]:
        q = self.embedder.embed([query])[0]
        scores = self.matrix @ q
        # small lexical bonus when a query term appears in a chunk's heading/title (hybrid re-rank)
        qt = {w for w in re.findall(r"[a-z]{3,}", query.lower())} - _STOP
        if qt:
            bonus = np.array([0.12 * len(qt & set(re.findall(r"[a-z]{3,}", f"{c.heading} {c.title}".lower()))) / len(qt)
                              for c in self.chunks])
            scores = scores + bonus
        order = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in order if scores[i] >= min_score]


def _key_sentences(text: str, query: str, n: int = 2) -> str:
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n(?=[-*] )", text) if len(s.split()) > 4]
    qwords = {w for w in re.findall(r"[a-z]{3,}", query.lower())}
    scored = sorted(sents, key=lambda s: -len(qwords & set(re.findall(r"[a-z]{3,}", s.lower()))))
    keep = scored[:n]
    return " ".join(s for s in sents if s in keep).lstrip("-* ").strip()


def _session_inference(ctx: dict | None) -> list[str]:
    """Statements about THIS session, derived from the emotion estimate/features (model inference)."""
    if not ctx:
        return []
    out = []
    emo = ctx.get("emotion")
    if emo:
        out.append(f"The model estimated your state as **{emo['label']}** (valence {emo['valence']:.0%}, arousal {emo['arousal']:.0%}, "
                   f"focus {emo['focus']:.0%}, stress tendency {emo['stress']:.0%}) with confidence {emo['confidence']:.0%}.")
        top = [f for f in emo.get("feature_importance", [])[:3]]
        if top:
            out.append("The features that moved the estimate most were " + ", ".join(
                f"{f['label']} ({f['direction']} {f['most_affects']})" for f in top) + ".")
    prof = ctx.get("profile")
    if prof:
        bits = [f"{prof['genre']}" if prof.get("genre") else None, f"{prof['bpm']} BPM" if prof.get("bpm") else None,
                prof.get("mode_name") or prof.get("key")]
        desc = " at ".join(b for b in [bits[0], bits[1]] if b) + (f" in {bits[2]}" if bits[2] else "")
        inst = prof.get("instrumentation") or []
        if desc.strip():
            out.append(f"The music strategy was **{desc}**" + (f" ({', '.join(inst[:3])})." if inst else "."))
    return out


class NeuroGuide:
    def __init__(self, llm: LLMProvider, embedder_name: str = "local-tfidf"):
        self.llm = llm
        self.store = VectorStore(load_chunks(), get_embedder(embedder_name))

    def ask(self, question: str, context: dict | None = None, k: int = 4) -> dict:
        hits = self.store.search(question, k=k)
        sources = [{"id": f"S{i + 1}", "doc": c.doc, "title": c.title, "heading": c.heading, "kind": c.kind,
                    "score": round(s, 3), "excerpt": c.text[:320]} for i, (c, s) in enumerate(hits)]
        inference = _session_inference(context)
        established_hits = [(c, s) for c, s in hits if c.kind == "science"]
        system_hits = [(c, s) for c, s in hits if c.kind == "system"]
        provider = "local-extractive"
        answer = None
        if self.llm.available() and hits:
            try:
                ctx_txt = "\n\n".join(f"[S{i + 1}] ({c.kind}) {c.title} – {c.heading}: {c.text}" for i, (c, _) in enumerate(hits))
                system = (
                    "You are NeuroGuide, an assistant in an experimental EEG-to-music research prototype. Answer ONLY using the "
                    "numbered sources and the session data. Structure the answer in two labelled sections: "
                    "'Established science' (cite sources like [S1]) and 'Model inference (this session)'. Never claim medical "
                    "diagnosis, never invent numbers, and say when sources do not cover the question. Be concise (under 180 words)."
                )
                user = f"Question: {question}\n\nSources:\n{ctx_txt}\n\nSession data:\n{' '.join(inference) or 'none'}"
                answer = self.llm.complete(system, user, max_tokens=420)
                provider = self.llm.name
            except LLMError:
                answer = None
        if answer is None:
            parts = []
            if established_hits:
                parts.append("**Established science** (from the knowledge base)")
                for i, (c, _) in enumerate(hits):
                    if c.kind == "science":
                        parts.append(f"- {_key_sentences(c.text, question)} [S{i + 1}]")
            if system_hits:
                parts.append("\n**How NeuroSonic works**")
                for i, (c, _) in enumerate(hits):
                    if c.kind == "system":
                        parts.append(f"- {_key_sentences(c.text, question)} [S{i + 1}]")
            if inference:
                parts.append("\n**Model inference (this session)**")
                parts += [f"- {s}" for s in inference]
            if not hits:
                parts = ["I could not find this in the knowledge base. I can answer questions about EEG frequency bands, "
                         "emotion recognition, music and emotion, signal processing, and how this system works."]
            answer = "\n".join(parts)
        return {"answer": answer, "sources": sources, "inference": inference, "provider": provider,
                "embedder": self.store.embedder.name, "disclaimer": DISCLAIMER}
