from fastembed import TextEmbedding

from ai_platform.config import settings

dense_model = TextEmbedding(settings.embed_model)
DIM = len(next(iter(dense_model.embed(["dim probe"]))))