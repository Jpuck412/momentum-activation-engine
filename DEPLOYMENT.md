# Deployment Guide

## 📋 Quick Start Deployment

### Option 1: Streamlit Cloud (⚡ Fastest - Recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select: `Jpuck412/momentum-activation-engine`
   - Choose: `app.py`
   - Click "Deploy"
   - **Done!** Auto-deploys on every push

3. **Access Your App**
   - https://momentum-activation-engine.streamlit.app

---

### Option 2: Docker Local Development

```bash
# Build image
docker build -t momentum-engine .

# Run container
docker run -p 8501:8501 momentum-engine

# Or use Docker Compose
docker-compose up -d
```

Access at: `http://localhost:8501`

---

### Option 3: Heroku (Traditional Deployment)

1. **Install Heroku CLI**
   ```bash
   brew install heroku
   heroku login
   ```

2. **Create Procfile** (add to repo root)
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```

3. **Deploy**
   ```bash
   heroku create your-momentum-app
   git push heroku main
   heroku logs --tail
   ```

4. **Access**
   - https://your-momentum-app.herokuapp.com

---

### Option 4: AWS (Cloud Run / Lambda)

**AWS App Runner (Easiest AWS option):**
```bash
# Push to ECR
aws ecr create-repository --repository-name momentum-engine
docker tag momentum-engine YOUR-ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/momentum-engine
docker push YOUR-ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/momentum-engine

# Deploy to App Runner
aws apprunner create-service \
  --service-name momentum-engine \
  --source-configuration RepositoryType=ECR,ImageRepository={ImageIdentifier=YOUR-ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/momentum-engine:latest}
```

---

### Option 5: Google Cloud Run (Easy & Scalable)

```bash
# Authenticate
gcloud auth login

# Build & push
gcloud builds submit --tag gcr.io/YOUR-PROJECT/momentum-engine

# Deploy
gcloud run deploy momentum-engine \
  --image gcr.io/YOUR-PROJECT/momentum-engine:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501
```

**Access:** https://momentum-engine-xxxxx.run.app

---

### Option 6: Azure App Service

```bash
# Create resource group
az group create --name momentum-rg --location eastus

# Create app service plan
az appservice plan create \
  --name momentum-plan \
  --resource-group momentum-rg \
  --sku B1 --is-linux

# Deploy
az webapp create \
  --resource-group momentum-rg \
  --plan momentum-plan \
  --name momentum-app \
  --deployment-container-image-name-user username \
  --deployment-container-image-name momentum-engine:latest
```

---

## 🎯 Recommended: Streamlit Cloud Setup

**Why Streamlit Cloud?**
- ✅ Free tier available
- ✅ Auto-deploys on git push
- ✅ No server management
- ✅ Built-in secrets management
- ✅ Perfect for this use case

**Steps:**
1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click "New app"
4. Choose your repo & app.py
5. **Deploy!**

---

## 🔒 Environment Variables (if needed)

Create `.streamlit/secrets.toml` (not in git):
```toml
api_key = "your-secret-key"
database_url = "postgres://..."
```

Access in app:
```python
api_key = st.secrets["api_key"]
```

---

## 📊 Production Checklist

- [ ] Push all files to main branch
- [ ] Test locally: `streamlit run app.py`
- [ ] Verify Docker builds: `docker build -t momentum-engine .`
- [ ] Choose deployment platform
- [ ] Deploy and test live
- [ ] Monitor performance
- [ ] Set up error alerts

---

## 🚀 What's Included

✅ `app.py` - Full trading engine (26KB, 600+ lines)
✅ `requirements.txt` - All dependencies
✅ `Dockerfile` - Container configuration
✅ `docker-compose.yml` - Local development
✅ `.streamlit/config.toml` - UI theme & settings
✅ `.github/workflows/ci.yml` - Auto tests on push
✅ `README.md` - Full documentation
✅ `LICENSE` - MIT open source

---

## 💡 Next Steps

1. **Deploy** using Streamlit Cloud (easiest)
2. **Share** the link with your team
3. **Monitor** performance & user engagement
4. **Iterate** based on feedback
5. **Scale** if needed to production infrastructure

---

## 📞 Support

- **Streamlit Docs:** https://docs.streamlit.io
- **GitHub Issues:** Create an issue in the repo
- **Yahoo Finance:** https://finance.yahoo.com

---

**Your app is production-ready! Deploy now! 🚀**
