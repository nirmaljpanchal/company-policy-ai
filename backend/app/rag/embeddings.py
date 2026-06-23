from openai import OpenAI

from app.config import get_settings

_client: OpenAI | None = None


def get_embedding_client() -> OpenAI:
    """Get or create a shared OpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Embed a list of texts.

    Args:
        texts: List of strings to embed
        batch_size: Process texts in batches (default 100)

    Returns:
        List of embedding vectors, one per input text

    Raises:
        ValueError: If inputs are empty or if embedding dimension doesn't match
    """
    if not texts:
        raise ValueError("No texts to embed")

    settings = get_settings()
    client = get_embedding_client()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model=settings.openai_embed_model,
        )

        for embedding_obj in response.data:
            vector = embedding_obj.embedding
            assert (
                len(vector) == settings.embed_dim
            ), f"Expected {settings.embed_dim}-dim vector, got {len(vector)}"
            all_embeddings.append(vector)

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """
    Embed a single query string.

    Args:
        text: String to embed

    Returns:
        Embedding vector

    Raises:
        ValueError: If text is empty or if embedding dimension doesn't match
    """
    if not text:
        raise ValueError("Text to embed cannot be empty")

    settings = get_settings()
    client = get_embedding_client()
    response = client.embeddings.create(
        input=text,
        model=settings.openai_embed_model,
    )

    vector = response.data[0].embedding
    assert (
        len(vector) == settings.embed_dim
    ), f"Expected {settings.embed_dim}-dim vector, got {len(vector)}"
    return vector
