#!/bin/bash

echo "Water Monitor Setup"
echo "==================="

# Check Python version
python3 --version || { echo "Python 3 is required"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers (this may take a few minutes)..."
playwright install chromium
playwright install-deps chromium

# Generate encryption key
echo ""
echo "Generating encryption key..."
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create .env file
echo "Creating .env file..."
cp .env.example .env
sed -i "s/your-generated-key-here/$ENCRYPTION_KEY/" .env

# Generate Flask secret key
FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed -i "s/change-this-to-a-random-string/$FLASK_SECRET/" .env

# Initialize database
echo "Initializing database..."
python3 manage.py init

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file to add your email settings for alerts (optional)"
echo "2. Add your meter accounts:"
echo "   python manage.py add_account"
echo ""
echo "3. Test the scraper with your first account:"
echo "   python manage.py inspect your-email@example.com your-password"
echo ""
echo "4. Start the application:"
echo "   python manage.py run"
echo ""
echo "The dashboard will be available at http://localhost:5000"
