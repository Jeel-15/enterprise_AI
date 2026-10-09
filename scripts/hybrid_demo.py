from ai_platform.vector_store import add_documents, hybrid_search, init_collection

DOCS = [
    {"text": "Customers can get their money back within 30 days of purchase.", "department": "support"},
    {"text": "Error ERR-4021 means the payment gateway timed out.", "department": "engineering"},
    {"text": "To reset your password, click Forgot Password on the login page.", "department": "support"},
    {"text": "Our GPU cluster uses vLLM for fast model inference.", "department": "engineering"},
    {"text": "Employees get 24 days of paid leave every year.", "department": "hr"},
    {"text": "Invoices are generated on the first day of each month.", "department": "finance"},
]


def show(title, results):
    print(f"\n=== {title} ===")
    for r in results:
        print(f"{r.score:.4f} | {r.payload['department']:<12} | {r.payload['text']}")


if __name__ == "__main__":
    init_collection()
    add_documents(DOCS)

    show("Semantic: 'refund rules'", hybrid_search("refund rules"))
    show("Keyword: 'ERR-4021'", hybrid_search("ERR-4021"))
    show("Filter: engineering only", hybrid_search("how fast is inference", department="engineering"))