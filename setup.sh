#!/bin/bash

# Install required packages
echo "Installing required packages..."
pip3 install Django>=5.2.8
pip3 install PyMuPDF>=1.23.0
pip3 install Pillow>=10.0.0
pip3 install requests>=2.31.0

# Create and apply migrations
echo "Creating migrations..."
python3 manage.py makemigrations file_processor

echo "Applying migrations..."
python3 manage.py migrate

# Create superuser (optional)
echo "To create a superuser, run: python3 manage.py createsuperuser"

echo "Setup complete! Run 'python3 manage.py runserver 0.0.0.0:8000' to start the server on all interfaces."