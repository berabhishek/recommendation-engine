import express from "express";
import session from "express-session";
import passport from "passport";
import { Strategy as LocalStrategy } from "passport-local";
import { initDB, createUser, findUserByUsername, findUserById, User } from "./db.ts";

const app = express();
const PORT = 3000;

// Initialize database
initDB();

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: "my-secret-key",
  resave: false,
  saveUninitialized: false
}));

// Passport Config
passport.use(new LocalStrategy(
  (username: string, password: string, done: (error: any, user?: any, info?: any) => void) => {
    try {
      const user = findUserByUsername(username);
      if (!user) {
        return done(null, false, { message: "Incorrect username." });
      }
      // Simple string comparison for demo, use bcrypt in real app
      if (user.password !== password) {
        return done(null, false, { message: "Incorrect password." });
      }
      return done(null, user);
    } catch (err) {
      return done(err);
    }
  }
));

passport.serializeUser((user: any, done: (err: any, id?: unknown) => void) => {
  done(null, user.id);
});

passport.deserializeUser((id: any, done: (err: any, user?: any) => void) => {
  try {
    const user = findUserById(id as number);
    if (user) {
      done(null, user);
    } else {
      done(new Error("User not found"));
    }
  } catch (err) {
    done(err);
  }
});

app.use(passport.initialize());
app.use(passport.session());

// Routes

// 1. Heartbeat
app.get("/heartbeat", (req: express.Request, res: express.Response) => {
  res.json({ status: "ok" });
});

// 2. Register
app.post("/register", (req: express.Request, res: express.Response) => {
  const { username, password } = req.body;
  if (!username || !password) {
    res.status(400).json({ error: "Username and password required" });
    return;
  }
  const user = createUser(username, password);
  if (user) {
    res.status(201).json({ message: "User created successfully", user });
  } else {
    res.status(500).json({ error: "Failed to create user or username already exists" });
  }
});

// 3. Login
app.post("/login", passport.authenticate("local"), (req: express.Request, res: express.Response) => {
  res.json({ message: "Logged in successfully", user: req.user });
});

// 4. Protected Route
const isAuthenticated = (req: express.Request, res: express.Response, next: express.NextFunction) => {
  if (req.isAuthenticated()) {
    return next();
  }
  res.status(401).json({ error: "Unauthorized" });
};

app.get("/protected", isAuthenticated, (req: express.Request, res: express.Response) => {
  res.json({ message: "You are authenticated", user: req.user });
});

// Start Server
if (import.meta.main) {
  app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

export { app };
