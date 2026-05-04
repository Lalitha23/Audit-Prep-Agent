from openai import OpenAI


class EmbeddingGenerator:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.client = OpenAI()
        self.model = model

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]
