# 🚀 Material AI v1.0 - Deployment Guide

## Pre-Flight Checklist ✅

### 1. System Requirements
- ✅ Python 3.10 or higher
- ✅ 2GB RAM minimum (4GB recommended)
- ✅ 1GB disk space
- ✅ Optional: CUDA-capable GPU for faster inference

### 2. Installation

```bash
# Clone repository
git clone <your-repo-url>
cd material_ai

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Initial Setup

```bash
# Train models (required for first-time setup)
python main.py train

# Verify installation
python main.py predict --current 150 --voltage 15 --speed 150
```

## 🌐 Deployment Options

### Option 1: Local Development

```bash
# Start Streamlit app
python main.py launch-app --port 8501

# Or start REST API
python main.py api --host 0.0.0.0 --port 8000
```

**Access:**
- Streamlit: http://localhost:8501
- API Docs: http://localhost:8000/docs

---

### Option 2: Docker Deployment

**Create Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Train models (or copy pre-trained models)
RUN python main.py train || echo "Using pre-trained models"

# Expose ports
EXPOSE 8000 8501

# Default command (API server)
CMD ["uvicorn", "api.rest_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run:**
```bash
# Build image
docker build -t material-ai:v1.0 .

# Run API server
docker run -p 8000:8000 material-ai:v1.0

# Run Streamlit app
docker run -p 8501:8501 material-ai:v1.0 \
  streamlit run app/streamlit_app.py --server.port 8501
```

---

### Option 3: Docker Compose (Recommended)

**Create docker-compose.yml:**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MATERIAL_AI_LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
    restart: unless-stopped
    command: uvicorn api.rest_api:app --host 0.0.0.0 --port 8000

  streamlit:
    build: .
    ports:
      - "8501:8501"
    environment:
      - MATERIAL_AI_LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
    restart: unless-stopped
    command: streamlit run app/streamlit_app.py --server.port 8501

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
      - streamlit
    restart: unless-stopped
```

**Deploy:**
```bash
docker-compose up -d
```

---

### Option 4: Kubernetes Deployment

**Create k8s-deployment.yaml:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: material-ai

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: material-ai-api
  namespace: material-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: material-ai-api
  template:
    metadata:
      labels:
        app: material-ai-api
    spec:
      containers:
      - name: api
        image: material-ai:v1.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        env:
        - name: MATERIAL_AI_LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: material-ai-api-service
  namespace: material-ai
spec:
  selector:
    app: material-ai-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: material-ai-api-hpa
  namespace: material-ai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: material-ai-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Deploy:**
```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -n material-ai
kubectl get svc -n material-ai
```

---

### Option 5: Cloud Platforms

#### AWS (Elastic Beanstalk)
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.10 material-ai

# Create environment
eb create material-ai-prod

# Deploy
eb deploy
```

#### Google Cloud Run
```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/material-ai

# Deploy
gcloud run deploy material-ai \
  --image gcr.io/PROJECT_ID/material-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure App Service
```bash
# Create resource group
az group create --name material-ai-rg --location eastus

# Create app service plan
az appservice plan create --name material-ai-plan \
  --resource-group material-ai-rg --sku B1 --is-linux

# Create web app
az webapp create --resource-group material-ai-rg \
  --plan material-ai-plan --name material-ai \
  --runtime "PYTHON|3.10"

# Deploy
az webapp up --name material-ai
```

---

## 🔧 Production Configuration

### Environment Variables

```bash
# Logging
export MATERIAL_AI_LOG_LEVEL=INFO
export MATERIAL_AI_LOG_DIR=logs

# Caching
export MATERIAL_AI_CACHE_DIR=.cache

# Monitoring
export MATERIAL_AI_METRICS_DIR=logs/metrics

# API
export MATERIAL_AI_API_HOST=0.0.0.0
export MATERIAL_AI_API_PORT=8000
```

### Nginx Configuration (nginx.conf)

```nginx
upstream api_backend {
    server api:8000;
}

upstream streamlit_backend {
    server streamlit:8501;
}

server {
    listen 80;
    server_name your-domain.com;

    # API
    location /api/ {
        proxy_pass http://api_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Streamlit
    location / {
        proxy_pass http://streamlit_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 📊 Monitoring Setup

### Prometheus (Optional)

**prometheus.yml:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'material-ai'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboard (Optional)

Import dashboard with metrics:
- Prediction volume
- Latency (P50, P95, P99)
- Error rate
- Success rate

---

## 🔒 Security Checklist

- [ ] Enable HTTPS (use Let's Encrypt or cloud provider SSL)
- [ ] Add API authentication (API keys or OAuth)
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable firewall rules
- [ ] Use secrets management (AWS Secrets Manager, etc.)
- [ ] Regular security updates
- [ ] Monitor access logs

---

## 🧪 Post-Deployment Testing

```bash
# Health check
curl http://your-domain.com/health

# Test prediction
curl -X POST http://your-domain.com/predict \
  -H "Content-Type: application/json" \
  -d '{"current_A": 150, "voltage_V": 15, "speed_mm_per_min": 150, "repair_stage": 0}'

# Check metrics
curl http://your-domain.com/metrics

# Load test (optional)
ab -n 1000 -c 10 -p request.json -T application/json \
  http://your-domain.com/predict
```

---

## 📈 Scaling Guidelines

### Horizontal Scaling
- **2-3 replicas**: Small workload (<100 req/min)
- **4-6 replicas**: Medium workload (100-500 req/min)
- **7-10 replicas**: High workload (500-1000 req/min)

### Vertical Scaling
- **1 CPU, 1GB RAM**: Development
- **2 CPU, 2GB RAM**: Small production
- **4 CPU, 4GB RAM**: Medium production
- **8 CPU, 8GB RAM**: High production

---

## 🔄 Maintenance

### Daily
- Check logs for errors
- Monitor metrics dashboard
- Verify health checks

### Weekly
- Review error rates
- Check disk space
- Update dependencies (if needed)

### Monthly
- Backup models and data
- Review performance metrics
- Plan capacity upgrades

---

## 🆘 Troubleshooting

### API Not Starting
```bash
# Check logs
docker logs <container-id>

# Verify models exist
ls -la models/saved/

# Test locally
python main.py api
```

### High Latency
```bash
# Check metrics
python main.py metrics show

# Monitor resources
docker stats

# Scale up
kubectl scale deployment material-ai-api --replicas=5
```

### Out of Memory
```bash
# Increase memory limit
docker run -m 4g material-ai:v1.0

# Or in K8s
# Update resources.limits.memory in deployment
```

---

## 📞 Support

- **Logs**: Check `logs/material_ai.log` and `logs/material_ai_errors.log`
- **Metrics**: Run `python main.py metrics show`
- **Health**: Check `/health` endpoint
- **Documentation**: See `API_DOCUMENTATION.md`

---

## ✅ Deployment Checklist

- [ ] Dependencies installed
- [ ] Models trained
- [ ] Tests passing
- [ ] Environment variables set
- [ ] SSL/HTTPS configured
- [ ] Monitoring enabled
- [ ] Backups configured
- [ ] Health checks working
- [ ] Load testing completed
- [ ] Documentation reviewed
- [ ] Team trained
- [ ] Rollback plan ready

---

## 🎉 You're Ready to Ship!

Material AI v1.0 is production-ready and world-class. Deploy with confidence! 🚀

**Need help?** Check the documentation or logs for troubleshooting.
