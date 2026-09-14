# HostelHub

A production-oriented Flask hostel discovery and booking platform for students, hostel owners, and administrators.

## Stack
- Flask + Flask-SQLAlchemy
- PostgreSQL in production (SQLite fallback for local development)
- Gunicorn
- Responsive custom UI
- Werkzeug password hashing

## Core workflows
- Student registration/login and booking requests
- Hostel owner registration, listings, booking management, and payment submissions
- Administrator dashboard, listing approval, booking visibility, and payment verification
- Hostel search, reviews, ratings, availability, and map links

## Production setup
Set these environment variables:
- `SECRET_KEY`: long random secret
- `DATABASE_URL`: PostgreSQL connection string
- `ADMIN_USERNAME`: initial administrator username
- `ADMIN_PASSWORD`: strong initial administrator password

Install dependencies, then run:

```bash
flask --app app init-db
gunicorn app:app
```

No demo users, demo hostels, or committed database are included.
