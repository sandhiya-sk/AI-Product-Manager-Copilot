"""
services/ingestion_service.py — Module 2 Data Ingestion Service

Handles file type/size validation, CSV parsing, schema checking, standard JSON conversion,
form parameter formatting, and bulk storing in the raw_feedback PostgreSQL database.
"""

import os
import uuid
from datetime import datetime, timezone
import pandas as pd
from werkzeug.datastructures import FileStorage

from database.db import db
from models.raw_feedback import RawFeedback
from utils.standardizer import normalize_priority, normalize_category, normalize_date

class IngestionService:
    @staticmethod
    def validate_csv_file(file_storage: FileStorage) -> tuple[bool, list[str]]:
        """
        Validate file storage type, size, and emptiness.
        """
        errors = []
        filename = file_storage.filename
        
        # 1. Validate MIME/Extension
        if not filename or not filename.lower().endswith('.csv'):
            errors.append("Invalid file type. Must be a .csv file.")
            return False, errors
            
        # 2. Check File Size (Read stream length)
        file_storage.seek(0, os.SEEK_END)
        size_bytes = file_storage.tell()
        file_storage.seek(0)  # Reset pointer
        
        max_size_mb = int(os.getenv("MAX_CSV_SIZE_MB", 10))
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if size_bytes > max_size_bytes:
            errors.append(f"File exceeds maximum allowed size of {max_size_mb} MB.")
            return False, errors
            
        if size_bytes == 0:
            errors.append("File is empty.")
            return False, errors
            
        return len(errors) == 0, errors

    @staticmethod
    def validate_csv_schema(df: pd.DataFrame) -> tuple[bool, list[str]]:
        """
        Ensure required columns exist (case-insensitive checking).
        Required: subject, description.
        """
        missing = []
        columns_lower = [str(col).lower().strip() for col in df.columns]
        
        if 'subject' not in columns_lower:
            missing.append('subject')
        if 'description' not in columns_lower:
            missing.append('description')
            
        if missing:
            return False, missing
        return True, []

    @staticmethod
    def parse_csv_to_records(
        df: pd.DataFrame, 
        user_id: uuid.UUID, 
        project_id: uuid.UUID, 
        filename: str, 
        batch_id: str
    ) -> tuple[list[dict], list[dict]]:
        """
        Parse DataFrame row by row and normalize each to canonical format.
        """
        valid_records = []
        failed_rows = []
        
        # Clean column names to lowercase and strip whitespace for uniform mapping
        df.columns = [str(col).lower().strip() for col in df.columns]
        
        for idx, row in df.iterrows():
            row_num = idx + 2  # 1-indexed plus header line is row 1
            
            # Row level validation
            subject = str(row.get('subject', '')).strip() if pd.notna(row.get('subject')) else ''
            description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else ''
            
            if not subject or not description:
                failed_rows.append({
                    "row_number": row_num,
                    "error": "Missing required fields: subject and description must be non-empty."
                })
                continue
                
            # Process values safely
            raw_feedback_id = str(row.get('feedback_id')) if pd.notna(row.get('feedback_id')) else str(uuid.uuid4())
            customer_name = str(row.get('customer_name')).strip() if pd.notna(row.get('customer_name')) else None
            customer_email = str(row.get('customer_email')).strip() if pd.notna(row.get('customer_email')) else None
            priority = normalize_priority(row.get('priority'))
            category = normalize_category(row.get('category'))
            product_name = str(row.get('product_name')).strip() if pd.notna(row.get('product_name')) else None
            product_version = str(row.get('product_version')).strip() if pd.notna(row.get('product_version')) else None
            
            sub_date = None
            if pd.notna(row.get('submission_date')):
                sub_date = normalize_date(row.get('submission_date'))
                
            tags_list = []
            if pd.notna(row.get('tags')) and str(row.get('tags')).strip():
                tags_list = [t.strip() for t in str(row.get('tags')).split(',') if t.strip()]
                
            sentiment = None
            if pd.notna(row.get('sentiment_self_reported')):
                sentiment = str(row.get('sentiment_self_reported')).strip()
                if sentiment not in ('Positive', 'Negative', 'Neutral'):
                    sentiment = None
                    
            language = str(row.get('language', 'en')).strip() if pd.notna(row.get('language')) else 'en'
            
            # Build canonical metadata dict
            metadata = {
                "original_filename": filename,
                "file_row_number": row_num,
                "ip_address": "0.0.0.0",  # Will be updated by request details
                "user_agent": "Unknown",  # Will be updated by request details
                "batch_id": batch_id
            }
            
            # Canonical JSON snapshot
            canonical_json = {
                "feedback_id": raw_feedback_id,
                "source": "csv_upload",
                "submitted_by_role": "product_manager",
                "user_id": str(user_id),
                "project_id": str(project_id),
                "customer_name": customer_name,
                "customer_email": customer_email,
                "subject": subject,
                "description": description,
                "priority": priority,
                "category": category,
                "product_name": product_name,
                "product_version": product_version,
                "submission_date": sub_date,
                "tags": tags_list,
                "sentiment_self_reported": sentiment,
                "language": language,
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "weight": 1,
                "duplicate_group_id": None,
                "processing_status": "pending"
            }
            
            record = {
                "feedback_id": raw_feedback_id,
                "source": "csv_upload",
                "submitted_by_role": "product_manager",
                "user_id": user_id,
                "project_id": project_id,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "subject": subject,
                "description": description,
                "priority": priority,
                "category": category,
                "product_name": product_name,
                "product_version": product_version,
                "submission_date": sub_date,
                "tags": tags_list,
                "sentiment_self_reported": sentiment,
                "language": language,
                "raw_metadata": metadata,
                "canonical_json": canonical_json,
                "weight": 1,
                "duplicate_group_id": None,
                "processing_status": "pending"
            }
            valid_records.append(record)
            
        return valid_records, failed_rows

    @staticmethod
    def parse_form_to_record(form_data: dict, user_id: uuid.UUID, project_id: uuid.UUID, role: str) -> dict:
        """
        Build a canonical record structure from manual text form data.
        """
        feedback_id = str(uuid.uuid4())
        subject = str(form_data.get('subject', '')).strip()
        description = str(form_data.get('description', '')).strip()
        priority = normalize_priority(form_data.get('priority'))
        category = normalize_category(form_data.get('category'))
        product_name = str(form_data.get('product_name', '')).strip() or None
        product_version = str(form_data.get('product_version', '')).strip() or None
        
        tags_raw = form_data.get('tags', [])
        tags_list = []
        if isinstance(tags_raw, str):
            tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
        elif isinstance(tags_raw, list):
            tags_list = [str(t).strip() for t in tags_raw if str(t).strip()]
            
        sentiment = form_data.get('sentiment_self_reported')
        if sentiment not in ('Positive', 'Negative', 'Neutral'):
            sentiment = None
            
        sub_date = normalize_date(form_data.get('submission_date')) or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        language = form_data.get('language', 'en')
        
        metadata = {
            "original_filename": None,
            "file_row_number": None,
            "ip_address": form_data.get('ip_address', '0.0.0.0'),
            "user_agent": form_data.get('user_agent', 'Unknown'),
            "batch_id": None
        }
        
        canonical_json = {
            "feedback_id": feedback_id,
            "source": "text_form",
            "submitted_by_role": role,
            "user_id": str(user_id),
            "project_id": str(project_id),
            "customer_name": form_data.get('customer_name') or None,
            "customer_email": form_data.get('customer_email') or None,
            "subject": subject,
            "description": description,
            "priority": priority,
            "category": category,
            "product_name": product_name,
            "product_version": product_version,
            "submission_date": sub_date,
            "tags": tags_list,
            "sentiment_self_reported": sentiment,
            "language": language,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "weight": 1,
            "duplicate_group_id": None,
            "processing_status": "pending"
        }
        
        return {
            "feedback_id": feedback_id,
            "source": "text_form",
            "submitted_by_role": role,
            "user_id": user_id,
            "project_id": project_id,
            "customer_name": form_data.get('customer_name') or None,
            "customer_email": form_data.get('customer_email') or None,
            "subject": subject,
            "description": description,
            "priority": priority,
            "category": category,
            "product_name": product_name,
            "product_version": product_version,
            "submission_date": sub_date,
            "tags": tags_list,
            "sentiment_self_reported": sentiment,
            "language": language,
            "raw_metadata": metadata,
            "canonical_json": canonical_json,
            "weight": 1,
            "duplicate_group_id": None,
            "processing_status": "pending"
        }

    @staticmethod
    def store_raw_feedback(records: list[dict]) -> int:
        """
        Store multiple raw_feedback records in database using bulk insert.
        """
        if not records:
            return 0
            
        objects = []
        for r in records:
            obj = RawFeedback(
                feedback_id=uuid.UUID(r['feedback_id']) if isinstance(r['feedback_id'], str) else r['feedback_id'],
                source=r['source'],
                submitted_by_role=r['submitted_by_role'],
                user_id=r['user_id'],
                project_id=r['project_id'],
                customer_name=r['customer_name'],
                customer_email=r['customer_email'],
                subject=r['subject'],
                description=r['description'],
                priority=r['priority'],
                category=r['category'],
                product_name=r['product_name'],
                product_version=r['product_version'],
                submission_date=r['submission_date'],
                tags=r['tags'],
                sentiment_self_reported=r['sentiment_self_reported'],
                language=r['language'],
                raw_metadata=r['raw_metadata'],
                canonical_json=r['canonical_json'],
                weight=r['weight'],
                duplicate_group_id=r['duplicate_group_id'],
                processing_status=r['processing_status']
            )
            objects.append(obj)
            
        db.session.bulk_save_objects(objects)
        db.session.commit()
        return len(objects)

    @staticmethod
    def get_feedback_status(feedback_id: str) -> dict:
        """
        Query database status for a specific feedback ID.
        """
        try:
            uuid_obj = uuid.UUID(feedback_id)
            record = RawFeedback.query.get(uuid_obj)
            if record:
                return record.to_status_dict()
        except ValueError:
            pass
        return None
