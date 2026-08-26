"""Ollama embeddings client + pure-Python kNN vector index.

If Ollama is unreachable (sandbox / offline demo), a deterministic
hash-seeded fallback vector is returned so the rest of the pipeline
still works. The fallback is documented in docs/framework-decision.md.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
import urllib.error
import urllib.request
from typing import Iterable

from ledger.config import EMBED_DIM, EMBED_MODEL, OLLAMA_HOST


def _fallback_vector(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic pseudo-embedding when Ollama is unreachable.

    SHA-256 seeded; L2-normalised. Cosine over these vectors still gives a
    stable ordering for similar inputs, which is enough for the kNN cache
    in this project.
    """
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    out: list[float] = []
    for i in range(dim):
        byte = seed[i % len(seed)]
        out.append(((byte / 127.5) - 1.0))
    norm = math.sqrt(sum(v * v for v in out)) or 1.0
    return [v / norm for v in out]


def embed(text: str, *, timeout: float = 10.0, allow_fallback: bool = True) -> list[float]:
    """Return an embedding for `text`. Tries Ollama first."""
    payload = json.dumps({"model": EMBED_MODEL, "input": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        if not allow_fallback:
            raise
        print(f"[embed] Ollama unreachable ({exc.__class__.__name__}); using fallback vector.", file=sys.stderr)
        return _fallback_vector(text)
    vec = data.get("embedding") or (data.get("embeddings") or [[]])[0]
    return [float(x) for x in vec]


def pack_floats(vec: Iterable[float]) -> bytes:
    return struct.pack(f"<{len(list(vec))}f", *vec)


def unpack_floats(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum((x / na) * (y / nb) for x, y in zip(a, b))


def store_embedding(cur, tx_id: int, vec: list[float]) -> None:
    cur.execute(
        "INSERT OR REPLACE INTO tx_embeddings (tx_id, vector) VALUES (?, ?)",
        (tx_id, pack_floats(vec)),
    )


def load_all(cur) -> list[tuple[int, list[float]]]:
    cur.execute("SELECT tx_id, vector FROM tx_embeddings")
    return [(int(row["tx_id"]), unpack_floats(bytes(row["vector"]))) for row in cur.fetchall()]


def knn(vector: list[float], k: int = 5) -> list[tuple[int, float]]:
    """Cosine-similarity kNN over all stored embeddings. Pure Python."""
    with _connect() as conn:
        cur = conn.cursor()
        rows = load_all(cur)
    scored = [(tx_id, cosine(vector, v)) for tx_id, v in rows if tx_id is not None]
    scored.sort(key=lambda r: r[1], reverse=True)
    return scored[:k]


def _connect():
    from ledger.db import connect  # local import avoids cycle

    return connect()


def nearest_category(
    vector: list[float],
    threshold: float = 0.92,
) -> tuple[str, int] | None:
    """Stable-cache lookup: nearest neighbour with a category, if similarity ≥ threshold."""
    from ledger.db import connect as db_connect
    with db_connect() as conn:
        cur = conn.cursor()
        rows = load_all(cur)
        scored = [(tx_id, cosine(vector, v)) for tx_id, v in rows]
        scored.sort(key=lambda r: r[1], reverse=True)
        if not scored:
            return None
        best_id, best_score = scored[0]
        if best_score < threshold:
            return None
        cur.execute("SELECT category FROM transactions WHERE id = ?", (best_id,))
        row = cur.fetchone()
        if not row or not row["category"]:
            return None
        return row["category"], int(best_id)


__all__ = [
    "embed",
    "pack_floats",
    "unpack_floats",
    "cosine",
    "store_embedding",
    "load_all",
    "knn",
    "nearest_category",
]