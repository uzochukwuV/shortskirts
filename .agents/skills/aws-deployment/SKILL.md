# AWS Deployment Skill

Deploy FastAPI applications to AWS using ECS Fargate, RDS, and ECR.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AWS Cloud                            │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────┐  │
│  │  ECS        │   │  RDS        │   │  ECR         │  │
│  │  Fargate    │◄──│  PostgreSQL │   │  Container   │  │
│  │  (API)      │   │  (Database) │   │  Registry    │  │
│  └──────┬──────┘   └─────────────┘   └──────────────┘  │
│         │                                              │
│  ┌──────▼──────┐   ┌─────────────┐   ┌──────────────┐  │
│  │  ALB        │   │  ElastiCache│   │  S3          │  │
│  │  (Load      │   │  (Redis)    │   │  (Assets)    │  │
│  │   Balancer) │   └─────────────┘   └──────────────┘  │
│  └──────┬──────┘                                       │
└─────────┼──────────────────────────────────────────────┘
```

## AWS Services Used

| Service | Purpose |
|---------|---------|
| ECS Fargate | Serverless container runtime |
| RDS PostgreSQL | Database |
| ElastiCache Redis | Job queue & caching |
| ECR | Container registry |
| ALB | Load balancer |
| S3 | Static assets, B2 backup |
| CloudWatch | Logging & metrics |
| Secrets Manager | API keys, tokens |
| ACM | SSL certificates |

## Deployment Steps

### 1. Build and Push Docker Image

```bash
# Build image
docker build -t shortskirts-api ./artifacts/pipeline

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REGISTRY
docker tag shortskirts-api:latest $ECR_REGISTRY/shortskirts-api:latest
docker push $ECR_REGISTRY/shortskirts-api:latest
```

### 2. Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name shortskirts-prod \
  --settings Name=containerInsights,Value=enabled
```

### 3. Create Task Definition

```json
{
  "family": "shortskirts-api",
  "cpu": "1024",
  "memory": "2048",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "containerDefinitions": [{
    "name": "api",
    "image": "$ECR_REGISTRY/shortskirts-api:latest",
    "portMappings": [{"containerPort": 8000}],
    "environment": [
      {"name": "DATABASE_URL", "value": "postgres://..."},
      {"name": "REDIS_URL", "value": "redis://..."}
    ],
    "secrets": [
      {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
      {"name": "DASHSCOPE_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
    ]
  }]
}
```

### 4. Create Service

```bash
aws ecs create-service \
  --cluster shortskirts-prod \
  --service-name shortskirts-api \
  --task-definition shortskirts-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[...],securityGroups=[...]}"
```

## Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| DATABASE_URL | RDS | PostgreSQL connection |
| REDIS_URL | ElastiCache | Redis for job queue |
| SECRET_KEY | Secrets Manager | API encryption |
| DASHSCOPE_API_KEY | Secrets Manager | Video generation |
| GOOGLE_CLIENT_ID | Secrets Manager | YouTube OAuth |
| TIKTOK_CLIENT_KEY | Secrets Manager | TikTok OAuth |
| B2_APPLICATION_KEY_ID | Secrets Manager | Storage |
| OPENAI_API_KEY | Secrets Manager | LLM |

## Cost Estimate (Monthly)

| Resource | Spec | Cost |
|----------|------|------|
| ECS Fargate | 2 tasks, 1vCPU, 2GB | ~$30 |
| RDS PostgreSQL | db.t3.medium | ~$50 |
| ElastiCache | cache.t3.micro | ~$15 |
| ALB | Basic | ~$16 |
| Data transfer | ~100GB | ~$10 |
| **Total** | | ~$121/month |
