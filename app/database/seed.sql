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

INSERT INTO expenses (category_id, title, amount, description, expense_date, recurrence)
VALUES
    ((SELECT id FROM expense_categories WHERE name = 'Groceries'), 'Weekly groceries', 42.30, 'Food and household supplies for the week', CURRENT_DATE, 'WEEKLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Housing'), 'Monthly rent', 850.00, 'Rent payment for the apartment', CURRENT_DATE - 5, 'MONTHLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Utilities'), 'Electricity bill', 68.45, 'Monthly electricity usage', CURRENT_DATE - 8, 'MONTHLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Dining Out'), 'Dinner with friends', 36.80, 'Dinner at a local restaurant', CURRENT_DATE - 2, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Transportation'), 'Train ticket', 24.90, 'Return ticket for a weekend trip', CURRENT_DATE - 12, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Healthcare'), 'Pharmacy purchase', 18.75, 'Medicine and vitamins', CURRENT_DATE - 4, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Subscriptions'), 'Music subscription', 10.99, 'Monthly music streaming plan', CURRENT_DATE - 10, 'MONTHLY'),
    ((SELECT id FROM expense_categories WHERE name = 'Entertainment'), 'Cinema tickets', 27.00, 'Two tickets for an evening movie', CURRENT_DATE - 6, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Shopping'), 'New headphones', 79.99, 'Replacement headphones for work', CURRENT_DATE - 15, 'NONE'),
    ((SELECT id FROM expense_categories WHERE name = 'Other'), 'Birthday gift', 31.50, 'Gift for a family member', CURRENT_DATE - 9, 'YEARLY');

INSERT INTO todos (
    title,
    description,
    priority,
    status,
    due_date
)
VALUES
('Implement todo API endpoints', 'Create CRUD endpoints for todos in the Life OS backend.', 'P1', 'in_progress', CURRENT_DATE),
('Add todo database model', 'Create the todos table/model with priority, status, due date, and timestamps.', 'P1', 'completed', CURRENT_DATE),
('Test todo creation endpoint', 'Send a POST request to create a new todo and verify it is saved correctly.', 'P1', 'not_started', CURRENT_DATE),
('Study CompTIA A+ virtualization module', 'Watch one hour of the Udemy course and write notes.', 'P2', 'not_started', CURRENT_DATE),
('Solve two LeetCode problems', 'Complete two coding problems and write down the pattern used.', 'P2', 'not_started', CURRENT_DATE),
('Reinstall Raspberry Pi with Ubuntu Server', 'Flash Ubuntu Server 24.04 LTS 64-bit and enable SSH.', 'P2', 'not_started', CURRENT_DATE + INTERVAL '1 day'),
('Install Docker on Raspberry Pi', 'Install Docker Engine and Docker Compose plugin.', 'P2', 'not_started', CURRENT_DATE + INTERVAL '1 day'),
('Create Docker Compose file for Life OS', 'Define backend, frontend, and database services.', 'P2', 'not_started', CURRENT_DATE + INTERVAL '2 days'),
('Check German course options', 'Ask schools about online or hybrid B2 Berufssprachkurs options.', 'P2', 'not_started', CURRENT_DATE),
('Update address with important offices', 'Create checklist for offices, bank, insurance, and tax office.', 'P2', 'not_started', CURRENT_DATE),
('Read German book for 15 minutes', 'Read German out loud and retell the section.', 'P3', 'not_started', CURRENT_DATE),
('Read English book for 15 minutes', 'Read English out loud for pronunciation and fluency.', 'P3', 'not_started', CURRENT_DATE),
('Prepare Tom job tool checklist', 'Review Notion checklist and prepare tools/materials.', 'P3', 'not_started', CURRENT_DATE + INTERVAL '3 days'),
('Back up Life OS repository', 'Push current backend and documentation changes to GitHub.', 'P2', 'not_started', CURRENT_DATE),
('Write README for Life OS backend', 'Document local setup, database setup, and API docs.', 'P3', 'not_started', CURRENT_DATE + INTERVAL '2 days');