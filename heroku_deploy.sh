#!/bin/bash

# Heroku Deployment Script for Car Rent System

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null
then
    echo "Heroku CLI is not installed. Please install it first."
    exit 1
fi

# Login to Heroku
heroku login

# Create a new Heroku app
APP_NAME="car-rent-system-$(date +%s)"
heroku create $APP_NAME

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(openssl rand -hex 32)

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:hobby-dev

# Push code to Heroku
git add .
git commit -m "Prepare for Heroku deployment"
git push heroku main

# Run database migrations
heroku run flask db upgrade

# Open the application
heroku open

echo "Deployment complete! Your app is available at https://$APP_NAME.herokuapp.com"
