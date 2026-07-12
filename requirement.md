we would be using python(flask) in the backend 



in this workflow -



we want to develop the project till module 3(inclusive)

we would be having both product managers and customers 

in csv we would be having fixed columns and fixed schema (so all the csvs that will be uploaded by product managers will have the same columns)

we would only be having csv (only for product managers , customers wont be able to upload csvs) and and text inputs can be given by the customer and the product manager (the text inputs will also be having particular fields specifying entire information) 

everything will be converted to json, the inputs from the csv files and the text inputs entered by product managers and customers will be converted to json 



the csv file(from managers) and the text input(from customers and managers) those fields will be present in the PostgreSQL (Raw Feedback Database) plus this postgres table should be comprehensive(it will also contain the metadata and many more hthings that would be useful and worth storing)



then send it to data processing and preprocessing pipeline -



in the first part of removing duplicates, we want to have semantic analysis, so whatever feedbacks we are having in PostgreSQL (Raw Feedback Database), we will fetch them and on the basis of semantic analysis we would be doing two things - 



removing duplicates and also counting the frequency of each review (so that if the sam review is given by multiple customers and demand is high we would be able to track it) , frequency of a review would be called "weight"



and then all of this would be performed -



Text Cleaning  Standardization  Metadata Generation

       │

       ▼

 Tokenization

       │

       ▼

 Lemmatization



and then we will store it in the PostgreSQL (Processed Feedback Database) and it will also have multiple columns (it will be a descriptive table having columns which would be important for the next modules)













PRODUCT MANAGER

                                          │

                                          ▼

                          React Frontend (Web Application)

                                          │

                    ┌─────────────────────┼─────────────────────┐

                    │                     │                     │

                    ▼                     ▼                     ▼

             Upload CSV             Upload JSON           Upload TXT

                    │                     │                     │

                    └─────────────────────┴─────────────────────┘

                                          │

                                          ▼

                         Module 2 – Data Ingestion Service

                                          │

          ┌────────────────────────────────────────────────────────────┐

          │                                                            │

          ▼                                                            ▼

   File Validation                                           File Parsing

(Type, Size, Schema, Empty File)                  (OpenCSV / Jackson / BufferedReader)

          │                                                            │

          └──────────────────────────────┬──────────────────────────────┘

                                         │

                                         ▼

                          Standard JSON Conversion

                                         │

                                         ▼

                       PostgreSQL (Raw Feedback Database)

                                         │

                                         ▼

               Module 3 – Data Processing & Preprocessing

                                         │

       ┌──────────────┬──────────────┬──────────────┬──────────────┐

       │              │              │              │

       ▼              ▼              ▼              ▼

 Remove Duplicates  Text Cleaning  Standardization  Metadata Generation

       │

       ▼

 Tokenization

       │

       ▼

 Lemmatization

       │

       ▼

              PostgreSQL (Processed Feedback Database)

                                         │

                                         ▼