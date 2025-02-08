# Environment Variables Management

## Purpose
Environment variables store configuration settings separately from code, enhancing security and flexibility.

## Required Variables for Car Rent System

### Production Environment
- `FLASK_ENV`: Set to `production`
  - Controls application behavior
  - Disables debug mode
  - Enables production-level security

- `SECRET_KEY`: Cryptographically secure random string
  - Used for session management
  - MUST be kept secret
  - Generate using: `python3 -c "import secrets; print(secrets.token_hex(32))"`

- `DATABASE_URL`: Database connection string
  - For PostgreSQL on Render
  - Provided by Render when creating a database
  - Format: `postgresql://username:password@host:port/database`

## Setting Variables

### Local Development
Create a `.env` file:
```
FLASK_ENV=development
SECRET_KEY=your_dev_secret_key
DATABASE_URL=sqlite:///dev.db
```

### Render Deployment
Set in Render Dashboard:
1. Web Service > Environment Tab
2. Add each variable individually
3. Keep values confidential

## Security Guidelines
- Never commit secret keys to version control
- Use different keys for development and production
- Rotate secrets periodically
- Limit access to environment variables

## Troubleshooting
- Verify all required variables are set
- Check variable names for exact match
- Ensure no extra spaces in values
