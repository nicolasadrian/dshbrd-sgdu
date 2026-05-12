-- Crear tabla de usuarios para autenticación
CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'user', -- 'admin' o 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- El password_hash para 'Nico1990' lo generaremos vía Python para asegurar que use bcrypt correctamente.
