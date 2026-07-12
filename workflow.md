AI PRODUCT MANAGER COPILOT



┌─────────────────────────────┐                          ┌─────────────────────────────┐

│      PRODUCT MANAGER        │                          │         CUSTOMER            │

└─────────────────────────────┘                          └─────────────────────────────┘

             │                                                       │

             │                                                       │

             ▼                                                       ▼

      Upload CSV                                         Submit Structured Feedback

 (Fixed Schema & Columns)                          (Subject, Description, Priority,

                                                    Category, Tags, etc.)

             │                                                       │

             └──────────────────────────────┬────────────────────────┘

                                            │

                                            ▼

                            React Frontend (Web Application)

                                            │

                                            ▼

                          Flask Backend (REST API + Module 2)

                                            │

                   ┌────────────────────────┴────────────────────────┐

                   │                                                 │

                   ▼                                                 ▼

            Input Validation                                 Data Parsing

   ───────────────────────────────                 ─────────────────────────────────

   CSV Schema Validation                           CSV Parser (Pandas)

   Required Columns                               Form Data Parser (Flask)

   Empty File Check                               JSON Object Creation

   Data Type Validation

                   │                                                 │

                   └────────────────────────┬────────────────────────┘

                                            ▼

                               Standard JSON Transformation

                                            │

                                            ▼

═══════════════════════════════════════════════════════════════════════════════

                  PostgreSQL – Raw Feedback Database

═══════════════════════════════════════════════════════════════════════════════

Stores:

• Original Feedback

• Standard JSON

• Source (Customer / Manager)

• Project ID

• User ID

• Upload Timestamp

• Processing Status

• Language

• Tags

• Raw Metadata

• Weight = 1 (Initially)

• Duplicate Group ID = NULL

• Additional Audit Information

═══════════════════════════════════════════════════════════════════════════════

                                            │

                                            ▼

                    Module 3 – Data Processing & Preprocessing

                                            │

                                            ▼

                            Fetch Raw Feedback Records

                                            │

                                            ▼

═══════════════════════════════════════════════════════════════════════════════

                    Semantic Duplicate Detection Engine

═══════════════════════════════════════════════════════════════════════════════

        Generate Embeddings

                │

                ▼

      Compare Semantic Similarity

                │

     ┌──────────┴──────────┐

     │                     │

Duplicate Found       New Feedback

     │                     │

     ▼                     ▼

Increase Weight       Weight = 1

Merge Records         Create New Entry

═══════════════════════════════════════════════════════════════════════════════

                                            │

                                            ▼

                                 Text Cleaning

                    • Remove Extra Spaces

                    • Remove HTML

                    • Remove URLs

                    • Remove Emojis

                    • Normalize Punctuation

                                            │

                                            ▼

                                 Standardization

                    • Lowercase Conversion

                    • Normalize Dates

                    • Normalize Status

                    • Normalize Priority

                                            │

                                            ▼

                                  Tokenization

                                            │

                                            ▼

                                  Lemmatization

                                            │

                                            ▼

                               Metadata Generation

                    • Word Count

                    • Character Count

                    • Processing Timestamp

                    • Weight

                    • Duplicate Group ID

                    • Source

                    • Project ID

                    • Processing Status

                                            │

                                            ▼

═══════════════════════════════════════════════════════════════════════════════

              PostgreSQL – Processed Feedback Database

═══════════════════════════════════════════════════════════════════════════════

Stores:

• Processed Feedback

• Clean Text

• Original Text

• Tokens

• Lemmatized Text

• Weight

• Duplicate Group ID

• Processing Metadata

• Project Information

• User Information

• Search Metadata

• Ready for Module 4

═══════════════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════════════

              PostgreSQL – Processed Feedback Database

═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

        Module 4 – Feedback Classification & Theme Extraction

═══════════════════════════════════════════════════════════════════════════════



                    Send Processed Feedback to Gemini



                                    │



                                    ▼



Gemini Extracts



• Category

• Theme

• Pain Points

• Keywords

• Sentiment

• Confidence Score



                                    │



                                    ▼



═══════════════════════════════════════════════════════════════════════════════

           PostgreSQL – Classified Feedback Database

═══════════════════════════════════════════════════════════════════════════════

Stores:



• Category

• Theme

• Keywords

• Sentiment

• Pain Points

• Confidence Score

• Weight

• Processed Feedback ID



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

        Module 5 – Feature Request Aggregation Engine

═══════════════════════════════════════════════════════════════════════════════



Group Similar Features



↓



Merge Similar Requests



↓



Count Total Weight



↓



Identify Trending Features



↓



Create Feature Repository



                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

              PostgreSQL – Feature Repository

═══════════════════════════════════════════════════════════════════════════════

Stores:



• Feature Name

• Theme

• Total Weight

• Supporting Feedback IDs

• Customer Count

• Trending Score



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

     Module 6 – AI Prioritization & Business Impact Analysis

═══════════════════════════════════════════════════════════════════════════════



Gemini receives



• Feature

• Weight

• Customer Segment

• Sentiment

• Theme



↓



Gemini Calculates



• Business Impact

• Customer Impact

• Estimated Effort

• Priority Score

• Recommended Priority



                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

           PostgreSQL – Prioritized Feature Repository

═══════════════════════════════════════════════════════════════════════════════



Stores:



• Priority Score

• Business Value

• Customer Impact

• Effort

• Recommendation



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

            Module 7 – Knowledge Base & Embedding Generation

═══════════════════════════════════════════════════════════════════════════════



Fetch



• Prioritized Features

• Processed Feedback

• Themes

• PRDs

• User Stories



↓



Gemini Embedding API



↓



Generate Embeddings



↓



Store Embeddings



                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

                    ChromaDB Vector Database

═══════════════════════════════════════════════════════════════════════════════



Stores



• Embedding Vector

• Original Document

• Metadata

• Feature ID

• Theme

• Priority

• Weight



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

              Module 8 – PRD Generation

═══════════════════════════════════════════════════════════════════════════════



Product Manager selects Feature



↓



RAG retrieves relevant feedback from ChromaDB



↓



Gemini generates



• Problem Statement

• Goals

• Functional Requirements

• Non-functional Requirements

• Risks

• Success Metrics



↓



Store Generated PRD



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

          Module 9 – User Story Generation

═══════════════════════════════════════════════════════════════════════════════



Gemini Generates



• User Stories



↓



Acceptance Criteria



↓



Definition of Done



↓



Store User Stories



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

             Module 10 – Roadmap Planning

═══════════════════════════════════════════════════════════════════════════════



Prioritized Features



↓



AI Groups



• Now



• Next



• Later



OR



• High



• Medium



• Low



↓



Generate Product Roadmap



↓



Store Roadmap



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

      Module 11 – Conversational Product Intelligence Assistant

═══════════════════════════════════════════════════════════════════════════════



User asks Question



↓



Embed Query



↓



Search ChromaDB



↓



Retrieve Relevant Context



↓



Gemini Flash



↓



Generate AI Response



═══════════════════════════════════════════════════════════════════════════════

                                    │

                                    ▼

═══════════════════════════════════════════════════════════════════════════════

              Module 12 – Reporting & Dashboard

═══════════════════════════════════════════════════════════════════════════════



React Dashboard



↓



Displays



• Feedback Analytics



• Top Pain Points



• Trending Features



• Priority Distribution



• Sentiment Analysis



• Product Roadmap



• AI Generated PRDs



• User Stories



• AI Chat Interface



═══════════════════════════════════════════════════════════════════════════════