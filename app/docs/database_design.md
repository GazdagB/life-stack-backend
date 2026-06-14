# Database Design 

## Version 1: Expense Tracking

### Tables

- expenses
- expense_categories

### expenses

| Column       | Type          | Notes                                |
|--------------|---------------|--------------------------------------|
| id           | SERIAL        | Primary Key                          
| category_id  | INTEGER       | Foreign key to expense_categories.id 
| amount       | NUMERIC(10,2) | REQUIRED                             |
| descreption  | TEXT          | Optional                             | 
| created_at   | TIMESTAMP     | Defaults to current timestamp        | 
| expense_date | DATE          | REQUIRED                             | 
| recurrence | VARCHAR(20) | NONE, DAILY, WEEKLY, MONTHLY, YEARLY (defaults to NONE)

### expense_categories

| Column       | Type          | Notes                                |
|--------------|---------------|--------------------------------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Required, unique |
