import os
import re

# Support disabling ChromaDB to save RAM on free-tier hosting (e.g. Render 512MB limit)
DISABLE_CHROMA = os.getenv("DISABLE_CHROMA", "false").lower() in ("true", "1")

# Defensively handle imports to support graceful degradation
CHROMA_AVAILABLE = False
if not DISABLE_CHROMA:
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        CHROMA_AVAILABLE = True
    except ImportError:
        print("Warning: chromadb or sentence-transformers not found. Local RAG will fall back to keyword matching.")
else:
    print("Info: ChromaDB and Sentence-Transformers disabled via DISABLE_CHROMA. Using keyword-matching fallback.")

class LocalVectorStore:
    def __init__(self, db_path: str = "./chroma_db"):
        self.db_path = os.path.abspath(db_path)
        self.collection_name = "activity_logs"
        self.model = None
        self.chroma_client = None
        self.collection = None
        self.fallback_db = [] # Fallback list of dicts: {"text": str, "metadata": dict, "id": str}

        if CHROMA_AVAILABLE:
            try:
                # Initialize persistent ChromaDB client
                self.chroma_client = chromadb.PersistentClient(path=self.db_path)
                
                # Load a fast, lightweight SentenceTransformer model (downloads on first run, ~90MB)
                self.model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
                
                # Get or create collection
                self.collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name
                )
                print(f"ChromaDB initialized at {self.db_path} with collection: {self.collection_name}")
            except BaseException as e:
                print(f"Warning: Failed to initialize ChromaDB: {e}. Purging folder and retrying...")
                import shutil
                try:
                    if os.path.exists(self.db_path):
                        shutil.rmtree(self.db_path)
                    self.chroma_client = chromadb.PersistentClient(path=self.db_path)
                    self.model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
                    self.collection = self.chroma_client.get_or_create_collection(
                        name=self.collection_name
                    )
                    print(f"ChromaDB initialized cleanly after purge at {self.db_path}")
                except BaseException as retry_err:
                    print(f"Warning: Failed to initialize ChromaDB after retry: {retry_err}. Falling back to memory search.")
                    self.chroma_client = None
                    self.collection = None

    def index_activities(self, activities: list, user_id: int):
        """Indexes a list of activity dictionaries into ChromaDB."""
        if not activities:
            return

        documents = []
        metadatas = []
        ids = []

        for act in activities:
            desc = act.get("description") or act.get("Description") or ""
            act_type = act.get("type") or act.get("Activity_Type") or "General"
            act_id = str(act.get("activity_id") or act.get("Activity_ID") or "")
            acc_id = str(act.get("account_id") or act.get("Account_ID") or "")
            act_date = str(act.get("date") or act.get("Activity_Date") or "")

            if not desc or not act_id:
                continue

            full_text = f"Activity Type: {act_type}\nDate: {act_date}\nDescription: {desc}"
            
            documents.append(full_text)
            metadatas.append({
                "account_id": acc_id,
                "activity_type": act_type,
                "activity_date": act_date,
                "activity_id": act_id,
                "user_id": user_id
            })
            ids.append(act_id)

            # Keep fallback memory representation updated
            self.fallback_db.append({
                "text": full_text.lower(),
                "metadata": {
                    "account_id": acc_id,
                    "activity_type": act_type,
                    "activity_date": act_date,
                    "activity_id": act_id,
                    "user_id": user_id
                },
                "id": act_id,
                "raw_desc": desc
            })

        if not documents:
            return

        if CHROMA_AVAILABLE and self.collection:
            try:
                # Generate embeddings
                embeddings = self.model.encode(documents).tolist()
                
                # Add to collection (upsert duplicates automatically using ID mapping)
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                print(f"Successfully indexed {len(ids)} activities in ChromaDB for user {user_id}.")
            except Exception as e:
                print(f"Error indexing to ChromaDB: {e}")
        else:
            print(f"Indexed {len(ids)} activities in fallback memory DB for user {user_id}.")

    def search_activities(self, query: str, user_id: int, account_id: str = None, limit: int = 3) -> list:
        """Retrieves most relevant activities semantically matching query."""
        if not query:
            return []

        # If Chroma is available, use vector search
        if CHROMA_AVAILABLE and self.collection:
            try:
                query_vector = self.model.encode(query).tolist()
                
                # Filter by user_id and optionally account_id
                if account_id:
                    where_filter = {
                        "$and": [
                            {"user_id": user_id},
                            {"account_id": account_id}
                        ]
                    }
                else:
                    where_filter = {"user_id": user_id}
                
                results = self.collection.query(
                    query_embeddings=[query_vector],
                    n_results=limit,
                    where=where_filter
                )
                
                retrieved = []
                if results and 'documents' in results and results['documents']:
                    docs = results['documents'][0]
                    metas = results['metadatas'][0]
                    for d, m in zip(docs, metas):
                        retrieved.append({
                            "text": d,
                            "metadata": m
                        })
                return retrieved
            except Exception as e:
                print(f"Chroma query error: {e}. Falling back to keyword match...")

        # Fallback to simple keyword/regex matching
        query_words = [w.lower() for w in re.split(r'\W+', query) if len(w) > 2]
        matches = []
        for item in self.fallback_db:
            # Apply user_id filter
            if item["metadata"].get("user_id") != user_id:
                continue
            # Apply account filter if specified
            if account_id and item["metadata"]["account_id"] != account_id:
                continue
            
            # Simple keyword score
            score = sum(1 for w in query_words if w in item["text"])
            if score > 0:
                matches.append((score, item))

        # Sort matches by score descending
        matches.sort(key=lambda x: x[0], reverse=True)
        return [{"text": item["text"], "metadata": item["metadata"]} for score, item in matches[:limit]]

# Singleton instance
vector_store = LocalVectorStore()
