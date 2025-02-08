# Render Deployment Guide for Car Rent System

## Prerequisites
- Render account
- GitHub repository
- Python 3.9+

## Deployment Steps

### 1. GitHub Repository
1. Push your project to GitHub
2. Ensure all files are committed

### 2. Render Web Service Setup
1. Log in to Render
2. Click "New Web Service"
3. Connect your GitHub repository
4. Configure deployment settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app`
   - Environment: Python 3.9+

### 3. Environment Variables
Set these in Render dashboard:
```
FLASK_ENV=production
SECRET_KEY=[generate a secure random key]
DATABASE_URL=[Render PostgreSQL connection string]
```

### 4. Database Configuration
1. Create a Render PostgreSQL database
2. Use the internal connection string
3. Add `DATABASE_URL` to environment variables

### 5. Post-Deployment
- Run database migrations
- Create admin user
- Test all functionalities

## Troubleshooting
- Check Render logs
- Verify environment variables
- Ensure all dependencies are in `requirements.txt`

## Security Recommendations
- Use strong, unique `SECRET_KEY`
- Limit database access
- Enable HTTPS
