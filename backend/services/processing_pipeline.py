"""
services/processing_pipeline.py — Module 3 Data Processing & Preprocessing Pipeline

Executes semantic duplicate detection, text cleaning, standardization, tokenization,
lemmatization, and stores processed records in processed_feedback.
"""

import os
import uuid
import time
from datetime import datetime, timezone
import numpy as np
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer

from database.db import db
from models.raw_feedback import RawFeedback
from models.processed_feedback import ProcessedFeedback

from utils.text_cleaner import clean_text
from utils.standardizer import standardize
from utils.tokenizer import tokenize
from utils.lemmatizer import lemmatize

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        
    def find(self, x):
        if self.parent[x] == x:
            return x
        # Path compression
        self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
        
    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y
            return True
        return False

class ProcessingPipeline:
    def __init__(self):
        self.model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.threshold = float(os.getenv("SIMILARITY_THRESHOLD", 0.85))
        
        # Load SentenceTransformer model
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Error loading SentenceTransformer '{self.model_name}': {e}. Using dummy embedding model fallback.")
            self.model = None

    def fetch_pending(self, project_id=None) -> list[RawFeedback]:
        """Fetch raw_feedback records with status 'pending'."""
        query = RawFeedback.query.filter_by(processing_status='pending')
        if project_id:
            query = query.filter_by(project_id=project_id)
        # Order by upload_timestamp ASC so oldest acts as canonical
        return query.order_by(RawFeedback.upload_timestamp.asc()).all()

    def detect_duplicates(self, records: list[RawFeedback]) -> list[dict]:
        """
        Group records by semantic similarity using cosine distance.
        Returns a list of groups with canonical, duplicates, and metadata.
        """
        if not records:
            return []
            
        n = len(records)
        full_texts = [f"{r.subject} {r.description}" for r in records]
        
        # Calculate embeddings
        if self.model:
            try:
                embeddings = self.model.encode(full_texts, show_progress_bar=False)
            except Exception as e:
                print(f"Embedding encoding failed: {e}. Falling back to exact text matching.")
                embeddings = None
        else:
            embeddings = None
            
        uf = UnionFind(n)
        
        # Compare pairwise similarity
        for i in range(n):
            for j in range(i + 1, n):
                is_duplicate = False
                if embeddings is not None:
                    try:
                        # Cosine similarity is 1 - Cosine distance
                        dist = cosine(embeddings[i], embeddings[j])
                        sim = 1.0 - dist
                        if sim >= self.threshold:
                            is_duplicate = True
                    except Exception as e:
                        print(f"Cosine distance computation error: {e}")
                        
                # Fallback: simple text match if embedding fails
                if embeddings is None or not is_duplicate:
                    if full_texts[i].strip().lower() == full_texts[j].strip().lower():
                        is_duplicate = True
                        
                if is_duplicate:
                    uf.union(i, j)
                    
        # Group indices by root parent
        groups_map = {}
        for i in range(n):
            root = uf.find(i)
            if root not in groups_map:
                groups_map[root] = []
            groups_map[root].append(i)
            
        groups = []
        for root_idx, indices in groups_map.items():
            # Sorted by upload_timestamp ASC since query was sorted ASC
            # Oldest record at indices[0] is the canonical
            canonical_idx = indices[0]
            dup_indices = indices[1:]
            
            group_id = str(uuid.uuid4())
            groups.append({
                "group_id": group_id,
                "canonical": records[canonical_idx],
                "duplicates": [records[idx] for idx in dup_indices],
                "weight": len(indices)
            })
            
        return groups

    def run(self, project_id=None) -> dict:
        """
        Runs the full processing pipeline.
        Returns processing stats.
        """
        records = self.fetch_pending(project_id)
        if not records:
            return {"processed": 0, "duplicates": 0, "failed": 0}
            
        # Transition all pending to processing first (bulk operation safety)
        for r in records:
            r.processing_status = 'processing'
        db.session.commit()
        
        groups = self.detect_duplicates(records)
        
        processed_count = 0
        duplicate_count = 0
        failed_count = 0
        
        for g in groups:
            canonical = g["canonical"]
            duplicates = g["duplicates"]
            group_weight = g["weight"]
            group_id = uuid.UUID(g["group_id"])
            
            start_time = time.time()
            
            try:
                # 1. Clean
                cleaned_desc = clean_text(canonical.description)
                
                # 2. Standardize
                standardized_desc = standardize(cleaned_desc)
                
                # 3. Tokenize
                tokens_list = tokenize(standardized_desc)
                
                # 4. Lemmatize
                lemmas_list = lemmatize(tokens_list)
                
                # Calculate processing duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 5. Build Metadata
                metadata = {
                    "nlp_model_version": "spacy-en_core_web_sm-3",
                    "embedding_model": self.model_name if self.model else "fallback-none",
                    "similarity_threshold_used": self.threshold,
                    "pipeline_version": os.getenv("PIPELINE_VERSION", "1.0.0"),
                    "processing_duration_ms": duration_ms
                }
                
                # 6. Save Processed Record
                processed_rec = ProcessedFeedback(
                    raw_feedback_id=canonical.feedback_id,
                    source=canonical.source,
                    submitted_by_role=canonical.submitted_by_role,
                    user_id=canonical.user_id,
                    project_id=canonical.project_id,
                    original_subject=canonical.subject,
                    original_description=canonical.description,
                    clean_text=cleaned_desc,
                    standardized_text=standardized_desc,
                    tokens=tokens_list,
                    lemmas=lemmas_list,
                    priority=canonical.priority,
                    category=canonical.category,
                    product_name=canonical.product_name,
                    product_version=canonical.product_version,
                    tags=canonical.tags,
                    sentiment_self_reported=canonical.sentiment_self_reported,
                    language=canonical.language,
                    submission_date=canonical.submission_date,
                    weight=group_weight,
                    duplicate_group_id=group_id,
                    word_count=len(cleaned_desc.split()) if cleaned_desc else 0,
                    char_count=len(cleaned_desc),
                    token_count=len(tokens_list),
                    lemma_count=len(lemmas_list),
                    processing_metadata=metadata,
                    processing_status='processed',
                    ready_for_classification=True
                )
                
                db.session.add(processed_rec)
                
                # Update Raw Canonical Record
                canonical.weight = group_weight
                canonical.duplicate_group_id = group_id
                canonical.processing_status = 'processed'
                canonical.processed_at = datetime.now(timezone.utc)
                processed_count += 1
                
            except Exception as e:
                db.session.rollback()
                print(f"Failed to process raw feedback {canonical.feedback_id}: {e}")
                canonical.processing_status = 'failed'
                canonical.processing_error = str(e)
                canonical.processed_at = datetime.now(timezone.utc)
                failed_count += 1
                
                # If canonical fails, processing still updates its status to failed
                db.session.commit()
                continue
                
            # Update Duplicate Raw Records
            for dup in duplicates:
                dup.duplicate_group_id = group_id
                dup.processing_status = 'duplicate'
                dup.processed_at = datetime.now(timezone.utc)
                duplicate_count += 1
                
            db.session.commit()
            
        return {
            "processed": processed_count,
            "duplicates": duplicate_count,
            "failed": failed_count
        }
