#!/bin/bash
# Document Agent Setup Script

echo "Document Agent Setup"
echo "==================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.12"

if [ "$(printf '%s
' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "[ERROR] Python 3.12 or higher is required (found $python_version)"
    exit 1
fi

echo "[OK] Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install uv
echo ""
echo "Installing uv package manager..."
pip install --upgrade pip
pip install uv

# Install dependencies with uv
echo ""
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "[INFO] Please edit .env and add your Anthropic API key"
fi

echo ""
echo "Setup complete!"
echo ""
echo "To run commands with uv:"
echo "  uv run python document_agent.py"
echo ""
echo "Or activate the environment manually:"
echo "  source venv/bin/activate"
echo ""
echo "To run the document agent:"
echo "  uv run python document_agent.py"
