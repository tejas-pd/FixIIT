CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'API',
    table_name TEXT,
    action TEXT NOT NULL,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_context (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    actor TEXT NOT NULL,
    source TEXT NOT NULL
);

INSERT INTO audit_context (id, actor, source)
VALUES (1, 'DIRECT_DB', 'DIRECT_DB');

CREATE TRIGGER trg_users_insert
AFTER INSERT ON users
BEGIN
    INSERT INTO logs (actor, source, table_name, action, details)
    SELECT actor, source, 'users', 'INSERT', 'user_id=' || NEW.id || ', username=' || NEW.username
    FROM audit_context
    WHERE id = 1;
END;

CREATE TRIGGER trg_users_update
AFTER UPDATE ON users
BEGIN
    INSERT INTO logs (actor, source, table_name, action, details)
    SELECT actor, source, 'users', 'UPDATE', 'user_id=' || NEW.id || ', username=' || NEW.username
    FROM audit_context
    WHERE id = 1;
END;

CREATE TRIGGER trg_users_delete
AFTER DELETE ON users
BEGIN
    INSERT INTO logs (actor, source, table_name, action, details)
    SELECT actor, source, 'users', 'DELETE', 'user_id=' || OLD.id || ', username=' || OLD.username
    FROM audit_context
    WHERE id = 1;
END;
