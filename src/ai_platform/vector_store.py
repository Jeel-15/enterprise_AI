from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models

from ai_platform.config import settings
from ai_platform.embeddings import DIM, dense_model

COLLECTION = "docs"

sparse_model = SparseTextEmbedding("Qdrant/bm25")

# Local mode: data settings.qdrant_path folder ma save thase
client = QdrantClient(path=settings.qdrant_path)


def _sparse(emb) -> models.SparseVector:
    return models.SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())


def init_collection() -> None:
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            "dense": models.VectorParams(size=DIM, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )


def add_documents(docs: list[dict]) -> None:
    texts = [d["text"] for d in docs]
    dense = list(dense_model.embed(texts))
    sparse = list(sparse_model.embed(texts))
    points = [
        models.PointStruct(
            id=i,
            vector={"dense": dense[i].tolist(), "bm25": _sparse(sparse[i])},
            payload=d,
        )
        for i, d in enumerate(docs)
    ]
    client.upsert(COLLECTION, points=points)


def hybrid_search(query: str, limit: int = 3, department: str | None = None):
    dense_q = next(iter(dense_model.query_embed(query))).tolist()
    sparse_q = _sparse(next(iter(sparse_model.query_embed(query))))

    flt = None
    if department:
        flt = models.Filter(
            must=[
                models.FieldCondition(
                    key="department", match=models.MatchValue(value=department)
                )
            ]
        )

    return client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            models.Prefetch(query=dense_q, using="dense", limit=20, filter=flt),
            models.Prefetch(query=sparse_q, using="bm25", limit=20, filter=flt),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=limit,
        with_payload=True,
    ).points