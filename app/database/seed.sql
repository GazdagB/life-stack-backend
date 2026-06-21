

INSERT INTO expense_categories (name)
VALUES ('Housing'),
       ('Utilities'),
       ('Groceries'),
       ('Dining Out'),
       ('Transportation'),
       ('Healthcare'),
       ('Subscriptions'),
       ('Entertainment'),
       ('Shopping'),
       ('Other');

INSERT INTO expenses (category_id, user_id, title, amount, description, expense_date, recurrence)
VALUES
    ((SELECT id FROM expense_categories WHERE name = 'Groceries'),1, 'Weekly groceries', 42.30, 'Food and household supplies for the week', CURRENT_DATE, 'WEEKLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Housing'),1, 'Monthly rent', 850.00, 'Rent payment for the apartment', CURRENT_DATE - 5, 'MONTHLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Utilities'),1, 'Electricity bill', 68.45, 'Monthly electricity usage', CURRENT_DATE - 8, 'MONTHLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Dining Out'),1, 'Dinner with friends', 36.80, 'Dinner at a local restaurant', CURRENT_DATE - 2, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Transportation'),1, 'Train ticket', 24.90, 'Return ticket for a weekend trip', CURRENT_DATE - 12, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Healthcare'),1, 'Pharmacy purchase', 18.75, 'Medicine and vitamins', CURRENT_DATE - 4, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Subscriptions'),1, 'Music subscription', 10.99, 'Monthly music streaming plan', CURRENT_DATE - 10, 'MONTHLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Entertainment'),1, 'Cinema tickets', 27.00, 'Two tickets for an evening movie', CURRENT_DATE - 6, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Shopping'),1, 'New headphones', 79.99, 'Replacement headphones for work', CURRENT_DATE - 15, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Other'),1, 'Birthday gift', 31.50, 'Gift for a family member', CURRENT_DATE - 9, 'YEARLY');

INSERT INTO todos (
    user_id,
    title,
    description,
    priority,
    status,
    due_date
)
VALUES
(1,'Implement todo API endpoints', 'Create CRUD endpoints for todos in the Life OS backend.', 'P1', 'in_progress', CURRENT_DATE),
(1,'Add todo database model', 'Create the todos table/model with priority, status, due date, and timestamps.', 'P1', 'completed', CURRENT_DATE),
(1,'Test todo creation endpoint', 'Send a POST request to create a new todo and verify it is saved correctly.', 'P1', 'not_started', CURRENT_DATE),
(1,'Study CompTIA A+ virtualization module', 'Watch one hour of the Udemy course and write notes.', 'P2', 'not_started', CURRENT_DATE),
(1,'Solve two LeetCode problems', 'Complete two coding problems and write down the pattern used.', 'P2', 'not_started', CURRENT_DATE),
(1,'Reinstall Raspberry Pi with Ubuntu Server', 'Flash Ubuntu Server 24.04 LTS 64-bit and enable SSH.', 'P2', 'not_started', CURRENT_DATE + INTERVAL '1 day'),
(1,'Install Docker on Raspberry Pi', 'Install Docker Engine and Docker Compose plugin.', 'P2', 'not_started', CURRENT_DATE + INTERVAL '1 day'),
(1,'Create Docker Compose file for Life OS', 'Define backend, frontend, and database services.', 'P2', 'not_started', CURRENT_DATE + INTERVAL '2 days'),
(1,'Check German course options', 'Ask schools about online or hybrid B2 Berufssprachkurs options.', 'P2', 'not_started', CURRENT_DATE),
(1,'Update address with important offices', 'Create checklist for offices, bank, insurance, and tax office.', 'P2', 'not_started', CURRENT_DATE),
(1,'Read German book for 15 minutes', 'Read German out loud and retell the section.', 'P3', 'not_started', CURRENT_DATE),
(1,'Read English book for 15 minutes', 'Read English out loud for pronunciation and fluency.', 'P3', 'not_started', CURRENT_DATE),
(1,'Prepare Tom job tool checklist', 'Review Notion checklist and prepare tools/materials.', 'P3', 'not_started', CURRENT_DATE + INTERVAL '3 days'),
(1,'Back up Life OS repository', 'Push current backend and documentation changes to GitHub.', 'P2', 'not_started', CURRENT_DATE),
(1,'Write README for Life OS backend', 'Document local setup, database setup, and API docs.', 'P3', 'not_started', CURRENT_DATE + INTERVAL '2 days');