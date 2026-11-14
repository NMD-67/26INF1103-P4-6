-- Fresh development database only. This is NOT a migration of existing tables.
-- Intentionally fails if tables exist; transaction prevents a partial setup.
BEGIN;
CREATE TABLE public.users (
    student_id TEXT CONSTRAINT users_student_id_key PRIMARY KEY,
    name TEXT,
    birthday DATE,
    age INTEGER,
    horoscope TEXT,
    gender TEXT,
    year TEXT,
    course TEXT,
    bio TEXT,
    race TEXT,
    religion TEXT,
    mbti TEXT,
    match_preference TEXT,
    here_for TEXT,
    expectations TEXT,
    tele_handle TEXT,
    insta_handle TEXT
);
CREATE TABLE public.ccas (
    student_id TEXT REFERENCES public.users(student_id) ON DELETE CASCADE,
    cca TEXT NOT NULL,
    PRIMARY KEY (student_id, cca)
);
CREATE TABLE public.events (
    student_id TEXT REFERENCES public.users(student_id) ON DELETE CASCADE,
    event TEXT NOT NULL,
    PRIMARY KEY (student_id, event)
);
CREATE TABLE public.hobbies (
    student_id TEXT REFERENCES public.users(student_id) ON DELETE CASCADE,
    hobby TEXT NOT NULL,
    PRIMARY KEY (student_id, hobby)
);
CREATE TABLE public.interests (
    student_id TEXT REFERENCES public.users(student_id) ON DELETE CASCADE,
    interest TEXT NOT NULL,
    PRIMARY KEY (student_id, interest)
);
CREATE TABLE public.dealbreakers (
    student_id TEXT PRIMARY KEY REFERENCES public.users(student_id) ON DELETE CASCADE,
    min_age INTEGER,
    max_age INTEGER,
    religion TEXT[] NOT NULL DEFAULT '{}',
    race TEXT[] NOT NULL DEFAULT '{}',
    gender TEXT,
    CHECK (min_age IS NULL OR min_age >= 0),
    CHECK (max_age IS NULL OR max_age >= 0),
    CHECK (min_age IS NULL OR max_age IS NULL OR min_age <= max_age)
);
CREATE TABLE public.matches (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES public.users(student_id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES public.users(student_id) ON DELETE CASCADE,
    compatibility_score INTEGER CHECK (compatibility_score BETWEEN 0 AND 100),
    interest_score INTEGER CHECK (interest_score BETWEEN 0 AND 100),
    personality_score INTEGER CHECK (personality_score BETWEEN 0 AND 100),
    preferences_score INTEGER CHECK (preferences_score BETWEEN 0 AND 100),
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    CONSTRAINT matches_student_candidate_unique UNIQUE (student_id, candidate_id),
    CHECK (student_id <> candidate_id)
);
-- OTPs must exist before a new user's account is created, so no users FK here.
CREATE TABLE public.otp (
    student_id TEXT PRIMARY KEY,
    otp INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE public.bot_users (
    tele_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES public.users(student_id) ON DELETE CASCADE
);
COMMIT;
