CREATE TABLE IF NOT EXISTS proxies (
    id SERIAL PRIMARY KEY,
    ip VARCHAR(50) NOT NULL,
    port INT NOT NULL,
    protocol VARCHAR(10) DEFAULT 'http',
    status INT DEFAULT 1, -- 1: available, 0: unavailable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user VARCHAR(50) NOT NULL,
    pw VARCHAR(50) NOT NULL
);

