# Campus Crush API

A social networking platform for campus community built with FastAPI.

## Features

- User authentication and management
- Post creation and management
- Comments on posts
- Reactions to posts (like, love, etc.)
- Friend requests and connections
- Notifications for user interactions
- Personalized home feed

## Project Structure

The application follows a modular architecture with the following modules:

- **Auth**: User authentication and authorization
- **User Management**: User profiles and settings
- **Posts**: Post creation and management
- **Comments**: Comments on posts
- **Reactions**: Reactions to posts
- **Friendships**: Friend requests and connections
- **Notifications**: User notifications
- **Home Feed**: Personalized feed of posts

## Setup

You can run the application directly on your machine.

### Local Setup

### Prerequisites

- Python 3.8+
- PostgreSQL

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/campus-crush.git
   cd campus-crush/backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a PostgreSQL database:
   ```
   createdb campus_crush_db
   ```

5. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration

6. Initialize the database:
   ```
   python init_db.py
   ```

### Running the Application

You can run the application using the provided `run.py` script:

```bash
# Basic usage (uses default settings)
python run.py

# Custom host and port
python run.py --host 127.0.0.1 --port 8080

# Force enable auto-reload
python run.py --reload
```

Available options:
- `--host`: Host to run the server on (default: 0.0.0.0)
- `--port`: Port to run the server on (default: 8000)
- `--reload`: Enable auto-reload on code changes (default: based on DEBUG setting)

The API will be available at http://localhost:8000 (or your specified host:port)

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

The API is organized into the following groups:

- `/api/v1/auth`: Authentication endpoints
- `/api/v1/users`: User management endpoints
- `/api/v1/posts`: Post management endpoints
- `/api/v1/comments`: Comment management endpoints
- `/api/v1/reactions`: Reaction management endpoints
- `/api/v1/friends`: Friendship management endpoints
- `/api/v1/notifications`: Notification management endpoints
- `/api/v1/feed`: Home feed endpoints

## Development

### Environment Variables

The application uses the following environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Secret key for JWT token generation
- `ALGORITHM`: Algorithm for JWT token generation
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time
- `MAIL_*`: Email service configuration
- `ALLOWED_EMAIL_DOMAINS`: Comma-separated list of allowed email domains
- `DEBUG`: Enable debug mode
- `ENVIRONMENT`: Current environment (development, production)

### Running Tests

The project includes a comprehensive test suite. To run the tests:

```bash
# Run all tests
pytest

# Run database tests specifically
pytest tests/test_db.py

# Run tests with detailed output
pytest -v

# Run tests and show coverage report
pytest --cov=app tests/
```

Before running tests, ensure you have:
1. PostgreSQL running
2. A test database will be created automatically (test_campus_crush_db)
3. The correct database URL in your .env file

The test suite includes:
- Database connection and transaction tests
- API endpoint tests (coming soon)
- Integration tests (coming soon)
- Unit tests (coming soon)

### Creating a Superuser

After setting up the database, you can create a superuser (admin) account:

```bash
# Using command-line arguments
python superuser.py --email admin@unilink.edu.pk --password your_secure_password --full-name "Admin User"

# The script will create a superuser account with elevated privileges
```

Superusers have additional privileges:
- Access to admin functionality
- User management capabilities
- System-wide moderation powers

## Google Sign-In Implementation

### Overview
This project now supports Google Sign-In authentication using Firebase. Google authentication allows users to sign in with their Google accounts without requiring a separate registration process.

### Configuration
1. Create a Firebase project at https://console.firebase.google.com/
2. Add your application to the Firebase project (Web, Android, iOS)
3. Enable Google as a sign-in provider in Firebase Authentication
4. Update the `.env` file with your Firebase API key:
   ```
   FIREBASE_API_KEY=your_firebase_api_key
   ```

### API Endpoint
`POST /api/v1/auth/google-signin`

Request body:
```json
{
  "firebase_token": "firebase_id_token_from_client",
  "email": "user@example.com",  // Optional, for verification
  "name": "User Name",          // Optional
  "photo_url": "https://..."    // Optional
}
```

Response:
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

### Frontend Integration
The client application should:
1. Implement Firebase authentication for Google Sign-In
2. After a successful Google Sign-In, get the Firebase ID token
3. Send the token to the server endpoint `/api/v1/auth/google-signin`
4. Use the returned JWT token for subsequent authenticated requests

### Error Handling
The endpoint returns appropriate error responses with status codes:
- 401 Unauthorized: Invalid Firebase token or authentication failed
- 400 Bad Request: Missing required fields or invalid request format
- 500 Internal Server Error: Server-side error during authentication

### Security Considerations
- Ensure Firebase API key is properly secured
- The backend validates Firebase tokens before creating or authenticating users
- Email verification status is inherited from Google's email verification
- Users created through Google Sign-In are automatically verified

## Database Management

### Migration Commands

The project uses Alembic for database migrations. Common operations can be performed using make commands:

```bash
# Apply all pending migrations
make db-migrate

# Create a new migration
make db-create message="description of changes"

# Downgrade to a specific revision
make db-downgrade revision=revision_id

# Verify schema changes
make db-verify

# Create database backup
make db-backup
```

### Manual Migration Commands

You can also use the management script directly:

```bash
# Apply migrations
python manage_db.py migrate

# Create new migration
python manage_db.py create "description of changes"

# Downgrade to specific revision
python manage_db.py migrate --downgrade revision_id

# Verify schema changes
python manage_db.py migrate --verify

# Skip backup during migration
python manage_db.py migrate --no-backup
```

### Database Backups

Backups are automatically created before migrations. They are stored in the `database_backups` directory with timestamps. 