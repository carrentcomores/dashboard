# Car Rental Management System

## Project Overview
A comprehensive car rental management system built with Flask, providing features for managing cars, bookings, clients, and financial tracking.

## Prerequisites
- Python 3.9+
- pip
- virtualenv (recommended)

## Deployment Instructions

### Local Development Setup
1. Clone the repository
```bash
git clone https://github.com/yourusername/car-rent-system.git
cd car-rent-system
```

2. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
Create a `.env` file in the project root with the following:
```
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///carrent.db
FLASK_ENV=production
```

5. Initialize the database
```bash
flask db upgrade
```

6. Run the application
```bash
python run.py
```

### Production Deployment

#### Option 1: Gunicorn (Recommended)
1. Install Gunicorn
```bash
pip install gunicorn
```

2. Run with Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

#### Option 2: Docker Deployment
1. Install Docker and Docker Compose
2. Build and run
```bash
docker-compose up --build
```

## Configuration
- Modify `config.py` for environment-specific settings
- Adjust database settings in `.env`

## Security Notes
- Always use a strong, unique `SECRET_KEY`
- Set `FLASK_ENV=production` in production
- Use environment variables for sensitive information

## Troubleshooting
- Ensure all dependencies are installed
- Check database migrations
- Verify environment variables

## License
[Your License Here]
# dashboard
