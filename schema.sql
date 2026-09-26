PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS firms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS advisor_users (
    id INTEGER PRIMARY KEY,
    firm_id INTEGER NOT NULL REFERENCES firms(id),
    username TEXT UNIQUE,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    firm_id INTEGER NOT NULL REFERENCES firms(id),
    business_name TEXT NOT NULL,
    industry TEXT NOT NULL,
    annual_revenue INTEGER NOT NULL CHECK (annual_revenue >= 0),
    ebitda INTEGER,
    employee_count INTEGER CHECK (employee_count >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_users (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    field_key TEXT NOT NULL UNIQUE,
    prompt TEXT NOT NULL,
    display_order INTEGER NOT NULL UNIQUE CHECK (display_order BETWEEN 1 AND 10)
);

CREATE TABLE IF NOT EXISTS answer_options (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    rating TEXT NOT NULL CHECK (rating IN ('high', 'medium', 'low')),
    answer_text TEXT NOT NULL,
    points INTEGER NOT NULL CHECK (points IN (0, 5, 10)),
    UNIQUE (question_id, rating),
    UNIQUE (question_id, id)
);

CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    question_id INTEGER NOT NULL REFERENCES questions(id),
    option_id INTEGER NOT NULL,
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (client_id, question_id),
    FOREIGN KEY (question_id, option_id) REFERENCES answer_options(question_id, id)
);

CREATE TABLE IF NOT EXISTS advisor_decisions (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    advisor_user_id INTEGER NOT NULL REFERENCES advisor_users(id),
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected', 'clarification')),
    note TEXT NOT NULL DEFAULT '',
    decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clients_firm ON clients(firm_id);
CREATE INDEX IF NOT EXISTS idx_responses_client ON questionnaire_responses(client_id);
CREATE INDEX IF NOT EXISTS idx_decisions_client ON advisor_decisions(client_id, id DESC);
