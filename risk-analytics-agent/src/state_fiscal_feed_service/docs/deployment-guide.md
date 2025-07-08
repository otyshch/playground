# Deployment Guide

## Overview

This guide covers deployment options for the State Fiscal Data Feed system, from local development to production environments.

## Prerequisites

### System Requirements

**Minimum Requirements**:
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- Network: 1Gbps

**Recommended for Production**:
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 100GB SSD
- Network: 10Gbps
- Load balancer support

### Software Dependencies

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.9+ (for local development)
- PostgreSQL 13+ with TimescaleDB
- Redis 6.0+

## Local Development Deployment

### Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd StateFiscalFeed
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database**:
   ```bash
   docker-compose exec api-service alembic upgrade head
   ```

5. **Verify deployment**:
   ```bash
   curl http://localhost:8000/health
   ```

### Service Endpoints

- **API Service**: http://localhost:8000
- **Streamlit Dashboard**: http://localhost:8501
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Local Development Commands

**Start specific services**:
```bash
# API only
docker-compose up api-service database redis

# Dashboard only
docker-compose up dashboard

# Monitoring stack
docker-compose up prometheus grafana
```

**View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api-service
```

**Run database migrations**:
```bash
docker-compose exec api-service alembic upgrade head
```

**Access database**:
```bash
docker-compose exec database psql -U postgres -d state_fiscal_feed
```

## Production Deployment

### Option 1: Docker Compose (Single Server)

**1. Production environment file**:
```bash
# .env.production
DATABASE_URL=postgresql://user:secure_password@db-server:5432/state_fiscal_feed
REDIS_URL=redis://redis-server:6379/0
TRADING_ECONOMICS_API_KEY=your_production_key
FRED_API_KEY=your_production_key
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

**2. Production compose file**:
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  database:
    image: timescale/timescaledb:latest-pg15
    environment:
      - POSTGRES_DB=state_fiscal_feed
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - backend

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - backend

  api-service:
    build: 
      context: .
      dockerfile: Dockerfile.api
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - TRADING_ECONOMICS_API_KEY=${TRADING_ECONOMICS_API_KEY}
      - FRED_API_KEY=${FRED_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - database
      - redis
    restart: unless-stopped
    networks:
      - backend
      - frontend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api-service
      - dashboard
    restart: unless-stopped
    networks:
      - frontend

volumes:
  postgres_data:
  redis_data:

networks:
  backend:
    driver: bridge
  frontend:
    driver: bridge
```

**3. Deploy production**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Kubernetes Deployment

**1. Namespace and ConfigMap**:
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: state-fiscal-feed

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: state-fiscal-feed
data:
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  LOG_LEVEL: "INFO"
  ENABLE_METRICS: "true"
```

**2. Database deployment**:
```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: state-fiscal-feed
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: timescale/timescaledb:latest-pg15
        env:
        - name: POSTGRES_DB
          value: state_fiscal_feed
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

**3. API service deployment**:
```yaml
# k8s/api-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  namespace: state-fiscal-feed
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-service
  template:
    metadata:
      labels:
        app: api-service
    spec:
      containers:
      - name: api-service
        image: state-fiscal-feed/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        - name: TRADING_ECONOMICS_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: trading-economics-key
        - name: FRED_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: fred-key
        envFrom:
        - configMapRef:
            name: app-config
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: state-fiscal-feed
spec:
  selector:
    app: api-service
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

**4. Ingress configuration**:
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: state-fiscal-feed
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.statefiscalfeed.com
    secretName: api-tls
  rules:
  - host: api.statefiscalfeed.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

**5. Deploy to Kubernetes**:
```bash
kubectl apply -f k8s/
```

### Option 3: Cloud Provider Deployment

#### AWS ECS with Fargate

**1. Task definition**:
```json
{
  "family": "state-fiscal-feed-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "api-service",
      "image": "account.dkr.ecr.region.amazonaws.com/state-fiscal-feed:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "API_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "API_PORT",
          "value": "8000"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:ssm:region:account:parameter/statefiscalfeed/database-url"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/state-fiscal-feed",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**2. Service definition**:
```json
{
  "serviceName": "state-fiscal-feed-api",
  "cluster": "production",
  "taskDefinition": "state-fiscal-feed-api",
  "desiredCount": 3,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-12345", "subnet-67890"],
      "securityGroups": ["sg-api-service"],
      "assignPublicIp": "DISABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:region:account:targetgroup/api-tg/123456",
      "containerName": "api-service",
      "containerPort": 8000
    }
  ],
  "serviceRegistries": [
    {
      "registryArn": "arn:aws:servicediscovery:region:account:service/srv-api"
    }
  ]
}
```

#### Google Cloud Run

**1. Build and push image**:
```bash
# Build image
docker build -t gcr.io/PROJECT-ID/state-fiscal-feed-api .

# Push to registry
docker push gcr.io/PROJECT-ID/state-fiscal-feed-api
```

**2. Deploy service**:
```bash
gcloud run deploy state-fiscal-feed-api \
  --image gcr.io/PROJECT-ID/state-fiscal-feed-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="API_HOST=0.0.0.0,API_PORT=8000" \
  --set-secrets="DATABASE_URL=database-url:latest,REDIS_URL=redis-url:latest" \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10
```

## Database Setup

### TimescaleDB Configuration

**1. Enable TimescaleDB extension**:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

**2. Create hypertable**:
```sql
SELECT create_hypertable('state_fiscal_data', 'data_timestamp');
```

**3. Create indexes**:
```sql
CREATE INDEX idx_state_timestamp ON state_fiscal_data (state_code, data_timestamp);
CREATE INDEX idx_data_timestamp ON state_fiscal_data (data_timestamp);
```

**4. Set up retention policy**:
```sql
SELECT add_retention_policy('state_fiscal_data', INTERVAL '7 years');
```

### Database Backup

**1. Automated backup script**:
```bash
#!/bin/bash
# backup-db.sh

DB_HOST="localhost"
DB_NAME="state_fiscal_feed"
DB_USER="postgres"
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -f "$BACKUP_DIR/backup_$DATE.sql"

# Compress backup
gzip "$BACKUP_DIR/backup_$DATE.sql"

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: backup_$DATE.sql.gz"
```

**2. Restore from backup**:
```bash
# Restore database
gunzip -c backup_20231231_120000.sql.gz | psql -h localhost -U postgres -d state_fiscal_feed
```

## Monitoring and Logging

### Prometheus Configuration

**1. Prometheus config** (`prometheus.yml`):
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'state-fiscal-feed-api'
    static_configs:
      - targets: ['api-service:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 30s
```

### Grafana Dashboards

**1. API Metrics Dashboard**:
- Request rate and latency
- Error rates by endpoint
- Database connection pool metrics
- Memory and CPU usage

**2. Data Quality Dashboard**:
- Data freshness metrics
- Record counts by state
- Ingestion success rates
- Data validation failures

### Log Aggregation

**1. Fluentd configuration**:
```yaml
# fluentd.conf
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<match docker.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name docker-logs
  type_name _doc
</match>
```

**2. Application logging**:
```python
import structlog

logger = structlog.get_logger(__name__)

# Log with context
logger.info(
    "API request processed",
    method="GET",
    path="/api/v1/fiscal-data/CA",
    status_code=200,
    duration_ms=125.5
)
```

## Security Considerations

### Network Security

**1. Firewall rules**:
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 5432/tcp   # Block direct DB access
ufw deny 6379/tcp   # Block direct Redis access
```

**2. TLS/SSL configuration**:
```nginx
# nginx SSL configuration
server {
    listen 443 ssl http2;
    server_name api.statefiscalfeed.com;
    
    ssl_certificate /etc/ssl/certs/api.statefiscalfeed.com.crt;
    ssl_certificate_key /etc/ssl/private/api.statefiscalfeed.com.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://api-service:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Application Security

**1. Environment variables**:
```bash
# Use strong passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# API keys with restricted permissions
TRADING_ECONOMICS_API_KEY=your_restricted_key
FRED_API_KEY=your_restricted_key
```

**2. Container security**:
```dockerfile
# Use non-root user
FROM python:3.9-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Read-only root filesystem
docker run --read-only --tmpfs /tmp state-fiscal-feed-api
```

## Performance Optimization

### Database Optimization

**1. Connection pooling**:
```python
# SQLAlchemy configuration
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

**2. Query optimization**:
```sql
-- Optimize common queries
EXPLAIN ANALYZE SELECT * FROM state_fiscal_data 
WHERE state_code = 'CA' AND data_timestamp <= '2023-12-31'
ORDER BY data_timestamp DESC LIMIT 1;

-- Add covering index
CREATE INDEX idx_state_latest ON state_fiscal_data 
(state_code, data_timestamp DESC) 
INCLUDE (state_tax_receipts_yoy_growth, state_budget_surplus_deficit_as_pct_of_gsp);
```

### Application Optimization

**1. Caching configuration**:
```python
# Redis caching
@cached(ttl=300)  # 5 minutes
def get_fiscal_data(state_code, date):
    return query_database(state_code, date)
```

**2. API optimization**:
```python
# Async endpoints
@app.get("/fiscal-data/{state}")
async def get_fiscal_data(state: str):
    return await fiscal_service.get_data(state)
```

## Troubleshooting

### Common Issues

**1. Database connection issues**:
```bash
# Check database status
docker-compose exec database pg_isready -U postgres

# View database logs
docker-compose logs database

# Test connection
psql -h localhost -U postgres -d state_fiscal_feed -c "SELECT 1;"
```

**2. High memory usage**:
```bash
# Monitor container memory
docker stats

# Check for memory leaks
docker-compose exec api-service python -m py_spy top --pid 1
```

**3. API performance issues**:
```bash
# Check API response times
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/health

# Monitor database connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'state_fiscal_feed';
```

### Health Checks

**1. Automated health monitoring**:
```bash
#!/bin/bash
# health-check.sh

API_URL="http://localhost:8000"
HEALTH_ENDPOINT="$API_URL/health/detailed"

response=$(curl -s -w "%{http_code}" -o /tmp/health.json "$HEALTH_ENDPOINT")

if [ "$response" -eq 200 ]; then
    status=$(jq -r '.status' /tmp/health.json)
    if [ "$status" = "healthy" ]; then
        echo "✅ System is healthy"
        exit 0
    else
        echo "❌ System is unhealthy"
        jq '.checks' /tmp/health.json
        exit 1
    fi
else
    echo "❌ Health check failed with HTTP $response"
    exit 1
fi
```

**2. Database health check**:
```sql
-- Check database health
SELECT 
    pg_database_size('state_fiscal_feed') / 1024 / 1024 as size_mb,
    count(*) as total_records,
    max(data_timestamp) as latest_data
FROM state_fiscal_data;
```

This deployment guide provides comprehensive coverage of deployment options from development to production, including monitoring, security, and troubleshooting guidance.