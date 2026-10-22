# RAG (NeuroGuide)

Code: `ml/neurosonic_ml/rag/engine.py`; knowledge in `ml/neurosonic_ml/rag/knowledge/*.md`.

```
markdown KB -> heading-aware chunking (<=110 words, 20-word overlap) -> embeddings -> in-memory vector store
question -> embed -> cosine search + heading-match bonus -> top-4 chunks -> (LLM | extractive composer) -> answer + sources
```

- **Knowledge base:** 7 documents covering EEG bands, EEG emotion recognition, music and emotion, music therapy/regulation,
  signal processing, limitations, and NeuroSonic's own behaviour. Each chunk is tagged `science` or `system`.
- **Embeddings:** `TfidfEmbedder` (1-2-grams, sublinear TF, fully local, no downloads). Set `EMBEDDING_PROVIDER=sentence-transformers`
  and install `sentence-transformers` for dense embeddings. Both implement `EmbeddingProvider`.
- **Vector store:** a NumPy matrix with cosine similarity. The corpus is tiny, so FAISS/Chroma would add dependencies without benefit;
  swapping one in only touches `VectorStore`.
- **Hybrid re-rank:** a small bonus when query terms appear in a chunk's heading/title (fixes TF-IDF over-weighting passing mentions).
- **Answer generation:** with an LLM, the prompt contains only numbered sources plus session data and demands two labelled sections.
  Without one, an extractive composer picks the most query-relevant sentences per source.
- **Science vs inference:** answers are split into **Established science** (retrieved text, cited `[S1]`), **How NeuroSonic works**
  (system docs) and **Model inference (this session)** (generated from the current estimate and top features). The UI lists sources with scores.
- **Unknown questions:** if nothing is retrieved above threshold, the assistant says so instead of guessing.

Extend the KB by adding `.md` files to the folder and restarting.
