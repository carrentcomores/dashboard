# Render Deployment Guide for Car Rent System

## Prerequisites
- Render account
- GitHub repository with your project
- Python 3.9+

## Deployment Steps

### 1. Prepare Your Repository
1. Ensure your project has:
   - `requirements.txt`
   - `run.py` as the main application entry point
   - `config.py` for configuration

### 2. Render Deployment
1. Log in to Render (https://render.com)
2. Create a new Web Service
3. Connect your GitHub repository
4. Configure deployment settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn run:app`
   - Environment: Python 3

### 3. Environment Variables
Set the following in Render's environment variables:
- `FLASK_ENV`: `production`
- `SECRET_KEY`: Generate a secure random key
- `DATABASE_URL`: Render PostgreSQL database connection string

### 4. Database Setup
- Create a Render PostgreSQL database
- Use the provided connection string in `DATABASE_URL`

### 5. Database Migrations
Run migrations after deployment:
```bash
render run flask db upgrade
```

## Troubleshooting
- Check Render logs for any deployment issues
- Ensure all dependencies are in `requirements.txt`
- Verify database connection string

## Performance Tips
- Use connection pooling
- Implement caching
- Optimize database queries
