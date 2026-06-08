import { DB } from "sqlite";

// Create/connect to the database file
export const db = new DB("database.sqlite");

// Initialize tables
export function initDB() {
  db.execute(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL
    )
  `);
}

// Simple ORM functions
export interface User {
  id: number;
  username: string;
  password?: string;
}

export function createUser(username: string, passwordHash: string): User | null {
  try {
    db.query("INSERT INTO users (username, password) VALUES (?, ?)", [username, passwordHash]);
    const row = db.query("SELECT id, username FROM users WHERE username = ?", [username]);
    if (row && row[0]) {
      return { id: row[0][0] as number, username: row[0][1] as string };
    }
    return null;
  } catch (error) {
    console.error("Error creating user:", error);
    return null;
  }
}

export function findUserByUsername(username: string): User | null {
  const row = db.query("SELECT id, username, password FROM users WHERE username = ?", [username]);
  if (row && row[0]) {
    return {
      id: row[0][0] as number,
      username: row[0][1] as string,
      password: row[0][2] as string
    };
  }
  return null;
}

export function findUserById(id: number): User | null {
  const row = db.query("SELECT id, username FROM users WHERE id = ?", [id]);
  if (row && row[0]) {
    return {
      id: row[0][0] as number,
      username: row[0][1] as string
    };
  }
  return null;
}
