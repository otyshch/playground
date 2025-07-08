# System Architecture Diagrams

## System Overview

```mermaid
graph TB
    subgraph "External Data Sources"
        TE[Trading Economics API]
        FRED[Federal Reserve FRED API]
    end
    
    subgraph "Data Ingestion Layer"
        DIS[Data Ingestion Service]
        CELERY[Celery Workers]
        REDIS[Redis Cache/Queue]
    end
    
    subgraph "Storage Layer"
        PG[PostgreSQL + TimescaleDB]
    end
    
    subgraph "API Layer"
        API[FastAPI Service]
        AUTH[Rate Limiting & Auth]
    end
    
    subgraph "Presentation Layer"
        DASH[Streamlit Dashboard]
        EXT[External Consumers]
    end
    
    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
        LOGS[Structured Logging]
    end
    
    TE --> DIS
    FRED --> DIS
    DIS --> CELERY
    CELERY --> REDIS
    CELERY --> PG
    
    PG --> API
    REDIS --> API
    API --> AUTH
    AUTH --> DASH
    AUTH --> EXT
    
    API --> PROM
    PG --> PROM
    REDIS --> PROM
    PROM --> GRAF
    
    API --> LOGS
    DIS --> LOGS
    CELERY --> LOGS
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant TE as Trading Economics
    participant FRED as FRED API
    participant DIS as Data Ingestion Service
    participant DB as TimescaleDB
    participant API as FastAPI
    participant DASH as Dashboard
    participant USER as End User
    
    Note over DIS: Scheduled Data Ingestion (Hourly)
    
    DIS->>TE: Request state tax data
    TE-->>DIS: Tax receipts data
    
    DIS->>FRED: Request GSP data
    FRED-->>DIS: GSP & budget data
    
    DIS->>DIS: Process & validate data
    DIS->>DIS: Calculate indicators
    
    alt Data validation passes
        DIS->>DB: Store fiscal indicators
    else Validation fails
        DIS->>DIS: Apply forward-fill
        DIS->>DB: Store forward-filled data
    end
    
    Note over USER: User Requests Data
    
    USER->>DASH: View state analysis
    DASH->>API: GET /api/v1/fiscal-data/CA
    API->>DB: Query latest data
    DB-->>API: Return fiscal data
    API-->>DASH: JSON response
    DASH-->>USER: Interactive charts
    
    USER->>API: Export bulk data
    API->>DB: Query historical data
    DB-->>API: Return data range
    API-->>USER: CSV download
```

## Component Architecture

```mermaid
graph TB
    subgraph "API Service"
        MAIN[main.py - FastAPI App]
        ROUTES[routers/ - Endpoint Handlers]
        SERVICES[services/ - Business Logic]
        MIDDLEWARE[middleware.py - Cross-cutting]
        DEPS[dependencies.py - DI]
        
        MAIN --> ROUTES
        ROUTES --> SERVICES
        MAIN --> MIDDLEWARE
        ROUTES --> DEPS
    end
    
    subgraph "Data Ingestion"
        EXTERNAL[external_apis.py - API Clients]
        DATA_SVC[data_service.py - Ingestion Logic]
        CELERY_APP[celery_app.py - Task Queue]
        
        DATA_SVC --> EXTERNAL
        CELERY_APP --> DATA_SVC
    end
    
    subgraph "Shared Components"
        MODELS[models.py - Data Models]
        CONFIG[config.py - Settings]
        DATABASE[database.py - DB Connection]
        
        SERVICES --> MODELS
        SERVICES --> DATABASE
        DATA_SVC --> MODELS
        DATA_SVC --> DATABASE
    end
    
    subgraph "Dashboard"
        DASH_APP[app.py - Streamlit App]
        DASH_API[API Client for Dashboard]
        
        DASH_APP --> DASH_API
        DASH_API --> MAIN
    end
```

## Database Schema

```mermaid
erDiagram
    STATE_FISCAL_DATA {
        int id PK
        string state_code "2-letter code"
        timestamp data_timestamp "Data date"
        float state_tax_receipts_yoy_growth "Tax growth %"
        float state_budget_surplus_deficit_as_pct_of_gsp "Budget % GSP"
        timestamp created_at "Record creation"
        timestamp updated_at "Last update"
    }
    
    STATE_FISCAL_DATA ||--o{ TIMESCALE_CHUNKS : "partitioned_by"
    
    TIMESCALE_CHUNKS {
        timestamp time_range_start
        timestamp time_range_end
        string chunk_name
    }
```

## API Request Flow

```mermaid
graph TD
    CLIENT[Client Request] --> LB[Load Balancer]
    LB --> NGINX[Nginx Reverse Proxy]
    NGINX --> RATE[Rate Limiting Middleware]
    RATE --> LOG[Logging Middleware]
    LOG --> CORS[CORS Middleware]
    CORS --> ROUTER[FastAPI Router]
    
    ROUTER --> VAL[Request Validation]
    VAL --> AUTH[Optional Authentication]
    AUTH --> BIZ[Business Logic Service]
    
    BIZ --> CACHE{Cache Hit?}
    CACHE -->|Yes| RETURN[Return Cached Data]
    CACHE -->|No| DB[Query Database]
    
    DB --> PROCESS[Process Results]
    PROCESS --> CACHE_STORE[Store in Cache]
    CACHE_STORE --> RETURN
    
    RETURN --> RESPONSE[Format Response]
    RESPONSE --> CLIENT
```

## Data Ingestion Architecture

```mermaid
graph TB
    subgraph "Scheduler"
        CRON[Cron/Celery Beat]
        SCHEDULE[Schedule Manager]
    end
    
    subgraph "Worker Pool"
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker N]
    end
    
    subgraph "External APIs"
        TE_API[Trading Economics]
        FRED_API[FRED]
    end
    
    subgraph "Processing Pipeline"
        FETCH[Data Fetcher]
        VALIDATE[Data Validator]
        TRANSFORM[Data Transformer]
        ENRICH[Data Enricher]
    end
    
    subgraph "Storage & Cache"
        PG_DB[(PostgreSQL)]
        REDIS_CACHE[(Redis Cache)]
        S3_BACKUP[(S3 Backup)]
    end
    
    CRON --> SCHEDULE
    SCHEDULE --> W1
    SCHEDULE --> W2
    SCHEDULE --> W3
    
    W1 --> FETCH
    W2 --> FETCH
    W3 --> FETCH
    
    FETCH --> TE_API
    FETCH --> FRED_API
    
    FETCH --> VALIDATE
    VALIDATE --> TRANSFORM
    TRANSFORM --> ENRICH
    
    ENRICH --> PG_DB
    ENRICH --> REDIS_CACHE
    PG_DB --> S3_BACKUP
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Internet"
        USER[End Users]
        API_CLIENTS[API Clients]
    end
    
    subgraph "CDN/Load Balancer"
        CF[CloudFlare/ALB]
        WAF[Web Application Firewall]
    end
    
    subgraph "Application Tier"
        subgraph "Kubernetes Cluster"
            POD1[API Pod 1]
            POD2[API Pod 2]
            POD3[API Pod 3]
            DASH_POD[Dashboard Pod]
            WORKER_POD[Worker Pods]
        end
        
        subgraph "Services"
            API_SVC[API Service]
            DASH_SVC[Dashboard Service]
        end
    end
    
    subgraph "Data Tier"
        PG_PRIMARY[(PostgreSQL Primary)]
        PG_REPLICA[(PostgreSQL Replica)]
        REDIS_CLUSTER[(Redis Cluster)]
    end
    
    subgraph "Monitoring"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        ELASTIC[ElasticSearch]
        KIBANA[Kibana]
    end
    
    subgraph "External Services"
        TRADING_ECON[Trading Economics API]
        FRED_SVC[FRED API]
    end
    
    USER --> CF
    API_CLIENTS --> CF
    CF --> WAF
    WAF --> API_SVC
    
    API_SVC --> POD1
    API_SVC --> POD2
    API_SVC --> POD3
    DASH_SVC --> DASH_POD
    
    POD1 --> PG_PRIMARY
    POD2 --> PG_PRIMARY
    POD3 --> PG_REPLICA
    
    POD1 --> REDIS_CLUSTER
    POD2 --> REDIS_CLUSTER
    POD3 --> REDIS_CLUSTER
    
    WORKER_POD --> TRADING_ECON
    WORKER_POD --> FRED_SVC
    WORKER_POD --> PG_PRIMARY
    
    POD1 --> PROMETHEUS
    POD2 --> PROMETHEUS
    POD3 --> PROMETHEUS
    DASH_POD --> PROMETHEUS
    
    PROMETHEUS --> GRAFANA
    POD1 --> ELASTIC
    POD2 --> ELASTIC
    POD3 --> ELASTIC
    ELASTIC --> KIBANA
```

## Security Architecture

```mermaid
graph TB
    subgraph "Network Security"
        INTERNET[Internet]
        WAF[Web Application Firewall]
        LB[Load Balancer]
        VPC[Virtual Private Cloud]
    end
    
    subgraph "Application Security"
        RATE_LIMIT[Rate Limiting]
        INPUT_VAL[Input Validation]
        CORS_POLICY[CORS Policy]
        API_VERSIONING[API Versioning]
    end
    
    subgraph "Data Security"
        DB_ENCRYPTION[Database Encryption at Rest]
        TLS[TLS/SSL in Transit]
        BACKUP_ENC[Encrypted Backups]
        ACCESS_LOGS[Access Logging]
    end
    
    subgraph "Infrastructure Security"
        IAM[Identity & Access Management]
        SECRETS[Secret Management]
        NETWORK_POLICY[Network Policies]
        CONTAINER_SEC[Container Security]
    end
    
    INTERNET --> WAF
    WAF --> LB
    LB --> VPC
    
    VPC --> RATE_LIMIT
    RATE_LIMIT --> INPUT_VAL
    INPUT_VAL --> CORS_POLICY
    CORS_POLICY --> API_VERSIONING
    
    API_VERSIONING --> DB_ENCRYPTION
    DB_ENCRYPTION --> TLS
    TLS --> BACKUP_ENC
    BACKUP_ENC --> ACCESS_LOGS
    
    ACCESS_LOGS --> IAM
    IAM --> SECRETS
    SECRETS --> NETWORK_POLICY
    NETWORK_POLICY --> CONTAINER_SEC
```

## Monitoring and Observability

```mermaid
graph TB
    subgraph "Application Metrics"
        APP_METRICS[Application Metrics]
        CUSTOM_METRICS[Custom Business Metrics]
        PERF_METRICS[Performance Metrics]
    end
    
    subgraph "Infrastructure Metrics"
        CPU_MEM[CPU/Memory]
        DISK_NET[Disk/Network]
        CONTAINER_METRICS[Container Metrics]
    end
    
    subgraph "Logs"
        APP_LOGS[Application Logs]
        ACCESS_LOGS[Access Logs]
        ERROR_LOGS[Error Logs]
        AUDIT_LOGS[Audit Logs]
    end
    
    subgraph "Collection"
        PROMETHEUS[Prometheus]
        FLUENTD[Fluentd]
        JAEGER[Jaeger Tracing]
    end
    
    subgraph "Storage"
        PROM_STORAGE[Prometheus Storage]
        ELASTIC[ElasticSearch]
        JAEGER_STORAGE[Jaeger Storage]
    end
    
    subgraph "Visualization"
        GRAFANA[Grafana Dashboards]
        KIBANA[Kibana]
        JAEGER_UI[Jaeger UI]
    end
    
    subgraph "Alerting"
        ALERT_MANAGER[AlertManager]
        PAGER_DUTY[PagerDuty]
        SLACK[Slack Notifications]
    end
    
    APP_METRICS --> PROMETHEUS
    CUSTOM_METRICS --> PROMETHEUS
    PERF_METRICS --> PROMETHEUS
    
    CPU_MEM --> PROMETHEUS
    DISK_NET --> PROMETHEUS
    CONTAINER_METRICS --> PROMETHEUS
    
    APP_LOGS --> FLUENTD
    ACCESS_LOGS --> FLUENTD
    ERROR_LOGS --> FLUENTD
    AUDIT_LOGS --> FLUENTD
    
    PROMETHEUS --> PROM_STORAGE
    FLUENTD --> ELASTIC
    JAEGER --> JAEGER_STORAGE
    
    PROM_STORAGE --> GRAFANA
    ELASTIC --> KIBANA
    JAEGER_STORAGE --> JAEGER_UI
    
    GRAFANA --> ALERT_MANAGER
    ALERT_MANAGER --> PAGER_DUTY
    ALERT_MANAGER --> SLACK
```

## Data Processing Pipeline

```mermaid
graph LR
    subgraph "External Data Sources"
        A[Trading Economics API]
        B[FRED API]
    end
    
    subgraph "Data Ingestion"
        C[API Clients]
        D[Data Validation]
        E[Data Transformation]
    end
    
    subgraph "Data Processing"
        F[YoY Growth Calculation]
        G[Budget % GSP Calculation]
        H[Data Enrichment]
    end
    
    subgraph "Data Quality"
        I[Validation Rules]
        J[Forward Fill Logic]
        K[Outlier Detection]
    end
    
    subgraph "Storage"
        L[TimescaleDB]
        M[Redis Cache]
        N[Backup Storage]
    end
    
    A --> C
    B --> C
    C --> D
    D --> E
    E --> F
    E --> G
    F --> H
    G --> H
    
    H --> I
    I -->|Valid| L
    I -->|Invalid| J
    J --> K
    K --> L
    
    L --> M
    L --> N
```

## Disaster Recovery Architecture

```mermaid
graph TB
    subgraph "Primary Region (US-East-1)"
        PRIMARY_APP[Primary Application]
        PRIMARY_DB[Primary Database]
        PRIMARY_CACHE[Primary Cache]
    end
    
    subgraph "Secondary Region (US-West-2)"
        SECONDARY_APP[Secondary Application]
        SECONDARY_DB[Secondary Database]
        SECONDARY_CACHE[Secondary Cache]
    end
    
    subgraph "Data Replication"
        DB_REPLICATION[Database Replication]
        CACHE_REPLICATION[Cache Replication]
        BACKUP_SYNC[Backup Synchronization]
    end
    
    subgraph "Monitoring & Failover"
        HEALTH_CHECK[Health Monitoring]
        FAILOVER_LOGIC[Automatic Failover]
        DNS_SWITCH[DNS Failover]
    end
    
    subgraph "Backup Storage"
        S3_PRIMARY[S3 Primary Backups]
        S3_SECONDARY[S3 Cross-Region Backups]
    end
    
    PRIMARY_DB --> DB_REPLICATION
    DB_REPLICATION --> SECONDARY_DB
    
    PRIMARY_CACHE --> CACHE_REPLICATION
    CACHE_REPLICATION --> SECONDARY_CACHE
    
    PRIMARY_DB --> S3_PRIMARY
    S3_PRIMARY --> BACKUP_SYNC
    BACKUP_SYNC --> S3_SECONDARY
    
    PRIMARY_APP --> HEALTH_CHECK
    SECONDARY_APP --> HEALTH_CHECK
    HEALTH_CHECK --> FAILOVER_LOGIC
    FAILOVER_LOGIC --> DNS_SWITCH
    
    DNS_SWITCH -->|Failover| SECONDARY_APP
```

These diagrams provide a comprehensive visual representation of the State Fiscal Feed system architecture, covering all major components, data flows, and operational aspects of the system.