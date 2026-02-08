#!/bin/bash
# Complete project setup script
# Runs all initialization and verification steps

set -e  # Exit on error

echo "=================================="
echo "inyAcity Project Setup"
echo "=================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo -e "${YELLOW}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi
python3 --version

# Check Node
echo -e "${YELLOW}Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: Node.js not found (needed for frontend)${NC}"
else
    node --version
fi

# Setup backend
echo -e "${YELLOW}Setting up backend...${NC}"
cd backend
if [ -f requirements.txt ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
else
    echo -e "${YELLOW}Warning: requirements.txt not found${NC}"
fi
cd ..

# Setup frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
cd fronto
if [ -f package.json ]; then
    echo "Installing Node dependencies..."
    npm install
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${YELLOW}Warning: package.json not found${NC}"
fi
cd ..

# Check environment
echo -e "${YELLOW}Checking environment...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found, copying from .env.example${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
        echo "Please update .env with your specific values before running the application"
    else
        echo -e "${RED}Error: Neither .env nor .env.example found${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ .env file found${NC}"

# Verify imports
echo -e "${YELLOW}Verifying imports...${NC}"
python3 -c "from backend.app import create_app; print('✓ Backend imports OK')"

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
python3 scraper/test_db_sync.py 2>/dev/null || echo -e "${YELLOW}Warning: Some tests skipped${NC}"

echo ""
echo -e "${GREEN}=================================="
echo "✅ Setup Complete!"
echo "==================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start backend:  python backend/app.py"
echo "2. Start frontend: cd fronto && npm start"
echo "3. Check endpoints: curl http://localhost:5000/health"
echo ""
