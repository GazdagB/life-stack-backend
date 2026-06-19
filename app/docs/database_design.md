# Database Design 

## Version 1: Expense Tracking

### Tables

- expenses
- expense_categories
- todos

### expenses

| Column       | Type          | Notes                                |
|--------------|---------------|--------------------------------------|
| id           | SERIAL        | Primary Key                          
| category_id  | INTEGER       | Foreign key to expense_categories.id 
| amount       | NUMERIC(10,2) | REQUIRED                             |
| description  | TEXT          | Optional                             | 
| created_at   | TIMESTAMP     | Defaults to current timestamp        | 
| expense_date | DATE          | REQUIRED                             | 
| recurrence | VARCHAR(20) | NONE, DAILY, WEEKLY, MONTHLY, YEARLY (defaults to NONE)

### expense_categories

| Column       | Type          | Notes                                |
|--------------|---------------|--------------------------------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Required, unique |


 ### todos
| Column      | Type         | Notes                                                   |
|-------------|--------------|---------------------------------------------------------|
| id          | SERIAL       | Primary Key                                             |
| title       | VARCHAR(120) | REQUIRED                                                |
 | description | TEXT         | Optional                                                |
| priority    | ENUM         | 'P1', 'P2' , 'P3', 'P4', 'P5'                           |
 | created_at  | TIMESTAMP    | Defaults to current timestamp                           | 
| updated_at  | TIMESTAMP | Updates whenever task changes                           |
 | due_date    | DATE         | Optional                                                |
| completed_at | TIMESTAMP | Null until completed                                    |
| status      | VARCHAR(20)  | 'Not Started', 'In Progress' , 'Completed', 'cancelled' | 
 | sort_order | INTEGER | Optional: for manual ordering later                     |
 | source | VARCHAR(50) | Optional: manual, cybro, import, system                 | 


### users 

| Column        | Type         | Notes                         |
|---------------|--------------|-------------------------------|
| id            | SERIAL  | Primary Key                   |
| username      | VARCHAR(20) | REQUIRED  UNIQUE              | 
| email         | VARCHAR(50) | REQUIRED  UNIQUE                    |
| password_hash | TEXT | hashed_password               |
| created_at | TIMESTAMP | CURRENT_TIMESTAMP ON CREATION | 

