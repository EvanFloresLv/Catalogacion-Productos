class EmbeddingError(Exception):
    pass


class TransientEmbeddingError(EmbeddingError):
    pass


class PermanentEmbeddingError(EmbeddingError):
    pass