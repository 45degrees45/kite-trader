#!/bin/bash
# setup.sh — One-time setup for Kite Trader on Ubuntu
set -e

echo "🔧 Setting up Kite Trader..."

# Python check
python3 --version || { echo "Python3 not found. Install with: sudo apt install python3 python3-pip"; exit 1; }

# Virtual environment
if [ ! -d "venv" ]; then
  python3 -m venv venv
  echo "✅ Virtual environment created"
fi

# Activate and install
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your KITE_API_KEY and KITE_API_SECRET"
echo "     (Get them from https://developers.kite.trade/)"
echo ""
echo "  2. Run the app:"
echo "     source venv/bin/activate && streamlit run app.py"
echo ""
echo "  3. Open http://localhost:8501 in your browser"
