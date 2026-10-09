import dspy

from ai_platform.vector_store import hybrid_search


class AnswerWithContext(dspy.Signature):
    """Answer the question using only the given context.
    If the context is not enough, say you don't know."""

    context: str = dspy.InputField()
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()


class RAG(dspy.Module):
    def __init__(self, k: int = 3):
        super().__init__()
        self.k = k
        self.generate = dspy.ChainOfThought(AnswerWithContext)

    def forward(self, question: str, department: str | None = None):
        hits = hybrid_search(question, limit=self.k, department=department)
        context = "\n".join(h.payload["text"] for h in hits)
        return self.generate(context=context, question=question)