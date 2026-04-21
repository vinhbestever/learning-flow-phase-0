erDiagram                                                                                                                                                                             
      PROGRAM_LESSON {                                                                                                                                                                  
          int id PK                                                                                                                                                                     
          int program_id                                                                                                                                                                
          int position                                                                                                                                                                  
          string title                                                                                                                                                                  
          string desc                                                                                                                                                                   
          int lesson_type                                                                                                                                                               
          int is_trial                                                                                                                                                                  
          int study_form                                                                                                                                                                
      }                                                                                                                                                                                 
                                                                                                                                                                                        
      PROGRAM_LESSON_SECTION {                                                                                                                                                          
          int id PK
          int lesson_id FK                                                                                                                                                              
          int program_id FK
          int lms_id FK                                                                                                                                                                 
          string title                                                                                                                                                                
          string desc
          int type "10=video, 4=practice"
          int position                                                                                                                                                                  
          int is_required
          string image                                                                                                                                                                  
          string software_used                                                                                                                                                        
          string link_study                                                                                                                                                             
          string link_practice                                                                                                                                                        
          string lms_link
          string start_time                                                                                                                                                             
          string end_time
          int lms_num_question                                                                                                                                                          
          int lms_duration                                                                                                                                                            
          int curriculum_section_id
      }                                                                                                                                                                                 
   
      TUTOR_LESSONS {                                                                                                                                                                   
          int id FK "= lesson ID"                                                                                                                                                     
          int lms_id FK                                                                                                                                                                 
          string title "lesson title"
          string section_type "Bài tập / Luyện tập"                                                                                                                                     
          string desc                                                                                                                                                                   
          int position
          int type                                                                                                                                                                      
          int lms_num_question                                                                                                                                                        
          int level                                                                                                                                                                     
          int completed_lesson                                                                                                                                                        
      }

      LMS_PRACTICE_RESULT {                                                                                                                                                             
          int id PK
          int site_id                                                                                                                                                                   
          int user_id                                                                                                                                                                 
          int practice_id FK "= lms_id"
          int course_id                                                                                                                                                                 
          string bai_lam
          string ket_qua                                                                                                                                                                
          string others                                                                                                                                                               
          int is_correct                                                                                                                                                                
          int status                                                                                                                                                                  
          float diem_thi "score 0-1"
          int total_correct_question                                                                                                                                                    
          int total_wrong_question                                                                                                                                                      
          int total_question                                                                                                                                                            
          int remain_time                                                                                                                                                               
          datetime create_date                                                                                                                                                        
          datetime update_date                                                                                                                                                          
          int create_user
          int update_user                                                                                                                                                               
          int level_id                                                                                                                                                                
      }

      LMS_PRACTICE_RESULT_DETAIL {                                                                                                                                                      
          int id PK
          int result_id FK                                                                                                                                                              
          int practice_id FK                                                                                                                                                          
          int question_id
          int site_id                                                                                                                                                                   
          int user_id
          int course_id                                                                                                                                                                 
          string content                                                                                                                                                              
          string answers
          string question_folder
          string question_type
          string comment                                                                                                                                                                
          string keywords
          string keywords_slug                                                                                                                                                          
          string bai_lam "raw answers (JSON)"               
          string ket_qua "graded answers (JSON)"                                                                                                                                        
          string others
          int is_correct                                                                                                                                                                
          datetime create_date                              
          datetime update_date
          int create_user
          int update_user                                                                                                                                                               
          int study_result_process
      }                                                                                                                                                                                 
                                                            
      LEARNING_SESSION {
          oid _id PK
          string studentId                                                                                                                                                              
          string erpLessonId FK "= lesson ID"
          oid scriptId                                                                                                                                                                  
          oid scriptVersionId                               
          int versionNumber
          string status                                                                                                                                                                 
          int attemptNumber
          int totalDurationMs                                                                                                                                                           
          int completionPercentage                          
          int totalFlows
          int completedFlowsCount
          int completedSectionsCount
          int totalSections                                                                                                                                                             
          datetime startedAt
          datetime lastActiveAt                                                                                                                                                         
          datetime completedAt                              
          datetime createdAt                                                                                                                                                            
          datetime updatedAt
          int __v                                                                                                                                                                       
      }                                                     

      LEARNING_SESSION_CHECKPOINT {
          oid sessionId FK
          array completedSections                                                                                                                                                       
          array completedFlows
          datetime lastCheckpointAt                                                                                                                                                     
      }                                                     

      LEARNING_RESULT {
          oid _id PK
          oid sessionId FK                                                                                                                                                              
          string studentId
          string erpLessonId FK                                                                                                                                                         
          string sectionId                                  
          oid scriptVersionId
          string flowId
          string nodeId
          string blockId
          string lmsType "practice"
          string interactionType "AUDIO"                                                                                                                                                
          int reactionTimeMs
          int attemptNumber                                                                                                                                                             
          array matchedVocabulary                                                                                                                                                       
          array matchedGrammar
          datetime timestamp                                                                                                                                                            
          datetime createdAt                                
          int __v
      }

      LEARNING_RESULT_LMS_DATA {                                                                                                                                                        
          oid resultId FK
          string moduleId                                                                                                                                                               
          string itemId                                     
          string questionType
          string question
          array answers
      }

      LEARNING_RESULT_SCORE {                                                                                                                                                           
          oid resultId FK
          float score                                                                                                                                                                   
          string audioUrl                                   
          string userTranscript
          object additionalData
          array userAnswers
      }

      PROGRAM_LESSON ||--o{ PROGRAM_LESSON_SECTION : "id = lesson_id"                                                                                                                   
      PROGRAM_LESSON_SECTION }o--o{ TUTOR_LESSONS : "lms_id"
      PROGRAM_LESSON_SECTION ||--o{ LMS_PRACTICE_RESULT : "lms_id = practice_id"                                                                                                        
      PROGRAM_LESSON ||--o{ TUTOR_LESSONS : "id = id"                                                                                                                                   
      LMS_PRACTICE_RESULT ||--o{ LMS_PRACTICE_RESULT_DETAIL : "id = result_id"                                                                                                          
      PROGRAM_LESSON ||--o{ LEARNING_SESSION : "id = erpLessonId"                                                                                                                       
      LEARNING_SESSION ||--|| LEARNING_SESSION_CHECKPOINT : "embedded"                                                                                                                  
      LEARNING_SESSION ||--o{ LEARNING_RESULT : "_id = sessionId"                                                                                                                       
      LEARNING_RESULT ||--|| LEARNING_RESULT_LMS_DATA : "embedded"                                                                                                                      
      LEARNING_RESULT ||--|| LEARNING_RESULT_SCORE : "embedded"

Lưu ý:                                                                                                                                                                                
  - LEARNING_SESSION_CHECKPOINT, LEARNING_RESULT_LMS_DATA, LEARNING_RESULT_SCORE là các object embedded (không phải bảng riêng), tách ra để thể hiện đầy đủ các trường.
