
from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "database" / "cameroon_smarttrip.db"

def hotel_corpus(df):
    cols = [
        "name","accommodation_type","beach_access","pool","wifi","restaurant",
        "family_friendly","key_features","address","booking_note"
    ]
    return df[cols].fillna("").astype(str).agg(" ".join, axis=1).tolist()

class HotelSemanticSearch:
    """
    Hybrid semantic search:
    - if sentence-transformers is installed, uses multilingual embeddings;
    - otherwise uses a fully local TF-IDF fallback.
    No external API key is required.
    """
    def __init__(self):
        con = sqlite3.connect(DB_PATH)
        self.hotels = pd.read_sql_query("SELECT * FROM vw_budget_hotels", con)
        con.close()
        self.texts = hotel_corpus(self.hotels)
        self.backend = "tfidf"
        self.model = None
        self.matrix = None
        self.vectorizer = None
        self._fit()

    def _fit(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            self.matrix = self.model.encode(
                self.texts, normalize_embeddings=True, show_progress_bar=False
            )
            self.backend = "sentence-transformers"
        except Exception:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(
                lowercase=True, strip_accents="unicode",
                ngram_range=(1,2), min_df=1
            )
            self.matrix = self.vectorizer.fit_transform(self.texts)
            self.backend = "tfidf"

    def search(self, query: str, top_k=10):
        if not query.strip():
            out = self.hotels.copy()
            out["semantic_score"] = 0.0
            return out.head(top_k)
        if self.backend == "sentence-transformers":
            q = self.model.encode([query], normalize_embeddings=True)[0]
            scores = np.dot(self.matrix, q)
        else:
            from sklearn.metrics.pairwise import cosine_similarity
            q = self.vectorizer.transform([query])
            scores = cosine_similarity(q, self.matrix).ravel()
        out = self.hotels.copy()
        out["semantic_score"] = scores
        return out.sort_values("semantic_score", ascending=False).head(top_k).reset_index(drop=True)

if __name__ == "__main__":
    engine = HotelSemanticSearch()
    print("Backend:", engine.backend)
    print(engine.search("hôtel familial calme près de la plage avec piscine et wifi", 5)[
        ["name","price_from_xaf","semantic_score"]
    ].to_string(index=False))
