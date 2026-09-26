"""Optional semantic search (install the `semantic` extra: fastembed + numpy).

Vectors are stored in SQLite and searched by brute-force cosine similarity, which is
fast enough for research workspaces (tens of thousands of chunks) and keeps the
system to a single file with no server.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from ..workspace import Workspace
from .store import Store

_MODELS: dict[str, object] = {}


def _model(name: str):
    from fastembed import TextEmbedding  # ImportError is handled by callers

    if name not in _MODELS:
        _MODELS[name] = TextEmbedding(model_name=name)
    return _MODELS[name]


def embed_missing(ws: Workspace, store: Store, progress: Callable[[str], None] | None = None) -> int:
    import numpy as np

    name = ws.config.get("semantic_model")
    rows = list(
        store.conn.execute(
            "SELECT c.id, d.title, c.section, c.text FROM chunks c JOIN docs d ON d.doc_id = c.doc_id "
            "LEFT JOIN vectors v ON v.chunk_id = c.id AND v.model = ? WHERE v.chunk_id IS NULL",
            (name,),
        )
    )
    if not rows:
        return 0
    if progress:
        progress(f"embedding {len(rows)} chunks with {name}")
    texts = [f"{r[1]} | {r[2]}\n{r[3]}"[:2000] for r in rows]
    vecs = list(_model(name).embed(texts, batch_size=32))
    cur = store.conn.cursor()
    cur.execute("BEGIN")
    for r, v in zip(rows, vecs):
        arr = np.asarray(v, dtype=np.float32)
        arr /= max(float(np.linalg.norm(arr)), 1e-9)
        cur.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?,?)", (r[0], name, arr.shape[0], arr.tobytes()))
    cur.execute("COMMIT")
    return len(rows)


def nearest(
    ws: Workspace, store: Store, queries: list[str], k: int, doc_ids: Iterable[str] | None = None
) -> list[tuple[int, float]]:
    import numpy as np

    name = ws.config.get("semantic_model")
    sql = "SELECT v.chunk_id, v.vec FROM vectors v JOIN chunks c ON c.id = v.chunk_id WHERE v.model = ?"
    args: list[object] = [name]
    ids = list(doc_ids or [])
    if ids:
        sql += f" AND c.doc_id IN ({','.join('?' * len(ids))})"
        args += ids
    rows = list(store.conn.execute(sql, args))
    if not rows:
        return []
    mat = np.stack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
    q = np.stack([np.asarray(v, dtype=np.float32) for v in _model(name).embed(queries)])
    q /= np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-9)
    sims = (mat @ q.T).max(axis=1)
    order = np.argsort(-sims)[:k]
    return [(int(rows[i][0]), float(sims[i])) for i in order]
