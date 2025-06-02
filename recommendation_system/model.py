from typing import Dict, List, Optional
from functools import partial
import numpy as np
import asyncio
import torch
from sentence_transformers import SentenceTransformer, util

ModelName = "distiluse-base-multilingual-cased-v1"  # Adequate for short labels


class RecommendationSystem:
    def __init__(self, db, model_name: str = ModelName):
        self.db = db
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device='cpu')
        self.theme_embeddings_cache: Optional[np.ndarray] = None
        self.theme_id_to_index = {}
        self.index_to_theme_id = {}
        self.specific_themes: List[str] = []

    def _embed_texts_sync(self, texts: List[str]) -> np.ndarray:
        """Generate BERT embeddings for a list of texts."""
        all_embeddings = []
        batch_size = 16
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                embeddings = self.model.encode(batch_texts, show_progress_bar=False)
                all_embeddings.append(embeddings)
        return np.vstack(all_embeddings)
    
    async def _embed_texts(self, texts: List[str]) -> np.ndarray:
        """Asynchronous wrapper for generating BERT embeddings."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,                      
            partial(self._embed_texts_sync, texts),
        )
    
    @staticmethod
    async def _cos_sim(a: torch.Tensor, b: torch.Tensor) -> np.ndarray:
        """Asynchronous wrapper for comparing cosine distances."""
        loop = asyncio.get_running_loop()
        similarities = await loop.run_in_executor(None, util.cos_sim, a, b)
        return similarities[0].numpy()

    async def _load_theme_embeddings(self):
        """Load all specific_theme texts and compute embeddings, cache them."""
        if self.theme_embeddings_cache is not None:
            return

        await self.db.connect()
        rows = await self.db.fetch("SELECT theme_id, specific_theme FROM themes ORDER BY theme_id")
        await self.db.close()

        self.theme_id_to_index = {}
        self.index_to_theme_id = {}
        self.specific_themes = []

        for idx, row in enumerate(rows):
            self.theme_id_to_index[row['theme_id']] = idx
            self.index_to_theme_id[idx] = row['theme_id']
            self.specific_themes.append(row['specific_theme'])

        self.theme_embeddings_cache = await self._embed_texts(self.specific_themes)

    async def get_user_history_embedding(self, user_id: int) -> Optional[np.ndarray]:
        """Aggregate embeddings of specific_themes from the last 12 user interactions."""
        await self._load_theme_embeddings()
        await self.db.connect()
        rows = await self.db.fetch(
            """
            SELECT t.specific_theme FROM user_activity_logs ual
            JOIN themes t ON ual.theme_id = t.theme_id
            WHERE ual.user_id = $1 AND ual.theme_id IS NOT NULL
            ORDER BY ual.request_time DESC
            LIMIT 12
            """,
            user_id
        )
        await self.db.close()

        if not rows:
            return None

        # Map specific_theme texts to indices in cached embeddings
        indices = []
        for row in rows:
            try:
                idx = self.specific_themes.index(row['specific_theme'])
                indices.append(idx)
            except ValueError:
                continue

        if not indices:
            return None

        user_embeddings = self.theme_embeddings_cache[indices]
        aggregated_embedding = np.mean(user_embeddings, axis=0, keepdims=True)
        return aggregated_embedding

    async def recommend(self, user_id: int, top_k: int = 5) -> List[Dict]:
        """Recommend books based on user history across specific_themes and experts."""
        import random
        await self._load_theme_embeddings()
        user_embedding = await self.get_user_history_embedding(user_id)
        if user_embedding is None:
            return []

        # Compute cosine similarity between user embedding and all theme embeddings
        similarities = await self._cos_sim(
            torch.tensor(user_embedding), torch.tensor(self.theme_embeddings_cache)
        )

        # Exclude themes user already interacted with
        await self.db.connect()
        user_theme_rows = await self.db.fetch(
            """
            SELECT theme_id FROM user_activity_logs
            WHERE user_id = $1 AND theme_id IS NOT NULL
            """,
            user_id
        )

        user_theme_ids = {row['theme_id'] for row in user_theme_rows}

        # Prepare list of (theme_id, similarity) excluding already seen
        candidates = [
            (self.index_to_theme_id[idx], sim)
            for idx, sim in enumerate(similarities)
            if self.index_to_theme_id[idx] not in user_theme_ids
        ]

        # Sort by similarity descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Fetch expert recommendations for top 10 themes
        top_candidates = candidates[:10]
        if not top_candidates:
            return []

        theme_ids = [c[0] for c in top_candidates]
        rows = await self.db.fetch(
            """
            SELECT
                t.theme_id,
                t.theme_name,
                t.specific_theme,
                e.expert_name,
                e.expert_position,
                b.book_name,
                er.description
            FROM themes t
            JOIN experts_recommendations er ON t.theme_id = er.theme_id
            JOIN experts e ON er.expert_id = e.expert_id
            JOIN books b ON er.book_id = b.book_id
            WHERE t.theme_id = ANY($1::int[])
            ORDER BY t.theme_id
            """,
            theme_ids
        )
        await self.db.close()

        # Organize recommendations by theme
        recommendations = {}
        for row in rows:
            theme_id = row['theme_id']
            if theme_id not in recommendations:
                recommendations[theme_id] = {
                    'theme_name': row['theme_name'],
                    'specific_theme': row['specific_theme'],
                    'experts': []
                }
            recommendations[theme_id]['experts'].append({
                'expert_name': row['expert_name'],
                'expert_position': row['expert_position'],
                'book_name': row['book_name'],
                'description': row['description']
            })

        # Randomly select 5 books from the top 10 recommendations
        all_recommendations = []
        for data in recommendations.values():
            all_recommendations.extend(data['experts'])

        selected_recommendations = random.sample(all_recommendations, min(top_k, len(all_recommendations)))

        # Group selected recommendations by theme for output
        output = []
        theme_map = {}
        for rec in selected_recommendations:
            theme_id = None
            for tid, data in recommendations.items():
                if rec in data['experts']:
                    theme_id = tid
                    break
            if theme_id is not None:
                if theme_id not in theme_map:
                    theme_map[theme_id] = {
                        'theme_name': recommendations[theme_id]['theme_name'],
                        'specific_theme': recommendations[theme_id]['specific_theme'],
                        'experts': []
                    }
                theme_map[theme_id]['experts'].append(rec)

        for theme_id, data in theme_map.items():
            output.append({
                'theme_name': data['theme_name'],
                'specific_theme': data['specific_theme'],
                'experts': data['experts']
            })

        return output
