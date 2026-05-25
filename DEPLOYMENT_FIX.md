# Deployment Instructions for Momentum Activation Engine

## Prerequisites
- Python 3.9 or higher
- pip, setuptools, and wheel upgraded

## Clean Installation Steps

### 1. Fresh Virtual Environment (REQUIRED)
```bash
# Remove any existing environment
rm -rf venv

# Create new environment
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### 2. Upgrade Core Tools (CRITICAL)
```bash
pip install --upgrade pip setuptools wheel
pip cache purge  # Clear pip cache
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Application
```bash
streamlit run app.py
```

## Troubleshooting

### If installation still fails:
1. **Clear everything:**
   ```bash
   deactivate
   rm -rf venv
   pip cache purge
   ```

2. **Try with constraints file:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install --upgrade pip setuptools wheel
   pip install --no-cache-dir -r requirements.txt
   ```

3. **For Windows users with build errors:**
   - Install Visual C++ Build Tools
   - Use Python 3.10+ (better Windows support)

### Common Issues:
- **"No module named pkg_resources"**: Upgrade setuptools: `pip install --upgrade setuptools`
- **Wheel building errors**: Use `--no-build-isolation` flag
- **Permission errors**: Use `--user` flag or create virtual environment

## Docker Alternative
If local installation fails, use Docker:
```bash
docker build -t momentum-engine .
docker run -p 8501:8501 momentum-engine
```
