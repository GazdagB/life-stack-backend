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


