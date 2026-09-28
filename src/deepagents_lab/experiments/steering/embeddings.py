"""Offline lexical vectors and an optional, cached OpenAI embedding backend."""
from hashlib import sha256
import json
from pathlib import Path
import re
from time import perf_counter
from typing import Protocol

import numpy as np


def normalized(values):
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError("Expected a finite embedding matrix.")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("Cannot normalize an empty/zero embedding.")
    return array / norms


class Embedder(Protocol):
    identity: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


class LexicalEmbedder:
    """Fixed hashed word/bigram counts. A wiring baseline, not semantic embeddings."""

    def __init__(self, dimensions: int = 512):
        if dimensions < 16:
            raise ValueError("Use at least 16 dimensions.")
        self.dimensions = dimensions
        self.identity = f"lexical-sha256-v1:{dimensions}"

    def embed(self, texts):
        result = np.zeros((len(texts), self.dimensions))
        for row, text in enumerate(texts):
            words = re.findall(r"[a-z]+", text.lower())
            features = words + [f"{a} {b}" for a, b in zip(words, words[1:])]
            for feature in features:
                digest = sha256(feature.encode()).digest()
                result[row, int.from_bytes(digest[:4], "big") % self.dimensions] += 1
        return normalized(result)


class OpenAIEmbedder:
    """One backend identity per cache. Requests and actual token usage are recorded."""

    def __init__(self, client, cache_dir: Path, model="text-embedding-3-small", dimensions=256):
        self.client, self.model, self.dimensions = client, model, dimensions
        self.identity = f"openai:{model}:{dimensions}"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.calls: list[dict] = []

    def embed(self, texts):
        paths = [self.cache_dir / (sha256(json.dumps([self.identity, t]).encode()).hexdigest() + ".json") for t in texts]
        missing = list(dict.fromkeys(i for i, path in enumerate(paths) if not path.exists()))
        if missing:
            started = perf_counter()
            call = {"kind": "embedding", "model": self.model, "inputs": len(missing), "ok": False}
            try:
                response = self.client.embeddings.create(
                    model=self.model, input=[texts[i] for i in missing], dimensions=self.dimensions,
                )
                call["usage"] = response.usage.model_dump()
                data = sorted(response.data, key=lambda item: item.index)
                if [item.index for item in data] != list(range(len(missing))):
                    raise ValueError("Embedding response did not cover requested inputs.")
                vectors = normalized([item.embedding for item in data])
                if vectors.shape != (len(missing), self.dimensions):
                    raise ValueError("Embedding dimension mismatch.")
                for i, vector in zip(missing, vectors):
                    paths[i].write_text(json.dumps(vector.tolist()))
                call["ok"] = True
            except Exception as error:
                call["error_type"] = type(error).__name__
                raise
            finally:
                call["elapsed_ms"] = (perf_counter() - started) * 1000
                self.calls.append(call)
        vectors = normalized([json.loads(path.read_text()) for path in paths])
        if vectors.shape != (len(texts), self.dimensions):
            raise ValueError("Cached embedding dimension mismatch.")
        return vectors
