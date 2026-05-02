# System Troubleshooting and FAQ

<cite>
**Referenced Files in This Document**
- [docs/troubleshooting.md](file://docs/troubleshooting.md)
- [docker-compose.yml](file://docker-compose.yml)
- [pyproject.toml](file://pyproject.toml)
- [scripts/run_admin.sh](file://scripts/run_admin.sh)
- [scripts/run_all.sh](file://scripts/run_all.sh)
- [scripts/run_llama_embeddings.sh](file://scripts/run_llama_embeddings.sh)
- [scripts/run_llama_llm.sh](file://scripts/run_llama_llm.sh)
- [scripts/run_ollama_llm.sh](file://scripts/run_ollama_llm.sh)
- [packages/rag_service/src/cafetera_rag_service/main.py](file://packages/rag_service/src/cafetera_rag_service/main.py)
- [packages/admin/src/cafetera_admin/main.py](file://packages/admin/src/cafetera_admin/main.py)
- [packages/vk_bot/src/cafetera_vk_bot/polling.py](file://packages/vk_bot/src/cafetera_vk_bot/polling.py)
- [packages/core/src/cafetera_core/config.py](file://packages/core/src/cafetera_core/config.py)
- [packages/core/src/cafetera_core/domain/errors.py](file://packages/core/src/cafetera_core/domain/errors.py)
- [packages/rag_service/src/cafetera_rag_service/config.py](file://packages/rag_service/src/cafetera_rag_service/config.py)
- [packages/admin/src/cafetera_admin/config.py](file://packages/admin/src/cafetera_admin/config.py)
- [packages/vk_bot/src/cafetera_vk_bot/config.py](file://packages/vk_bot/src/cafetera_vk_bot/config.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Common Issues and Solutions](#common-issues-and-solutions)
3. [Docker and Container Problems](#docker-and-container-problems)
4. [Port Conflicts](#port-conflicts)
5. [Model Loading and Performance Issues](#model-loading-and-performance-issues)
6. [VK Bot Integration Problems](#vk-bot-integration-problems)
7. [Local Development Environment](#local-development-environment)
8. [Advanced Troubleshooting](#advanced-troubleshooting)
9. [Preventive Measures](#preventive-measures)
10. [When to Seek Additional Help](#when-to-seek-additional-help)

## Introduction

This comprehensive troubleshooting guide addresses the most frequent issues encountered when setting up and operating the cafetera_hr_bot system. The guide covers Docker deployment problems, port conflicts, model loading issues, VK bot integration challenges, and local development environment concerns. Whether you're deploying the system for the first time or dealing with ongoing operational issues, this guide provides systematic approaches to diagnose and resolve problems efficiently.

The system consists of four main components: the RAG service for document processing and retrieval, the administrative interface for document management, the VK bot for community interaction, and supporting infrastructure including Qdrant vector database, MinIO object storage, and PostgreSQL database.

## Common Issues and Solutions

### Docker Command Not Found

**Problem**: The system reports "docker: command not found" during deployment attempts.

**Diagnosis Steps**:
1. Verify Docker installation status
2. Check Docker daemon availability
3. Confirm Docker Compose compatibility

**Solution**: Install Docker Desktop or Docker Engine according to your operating system requirements. Ensure Docker is running before attempting deployments.

**Section sources**
- [docs/troubleshooting.md:7-11](file://docs/troubleshooting.md#L7-L11)

### uv Command Not Found

**Problem**: The development environment reports "uv: command not found".

**Diagnosis Steps**:
1. Close and reopen terminal sessions
2. Verify shell configuration files
3. Check PATH environment variable

**Solution**: Reinstall uv using the official installer script. After installation, restart your terminal session to ensure PATH updates are recognized.

**Section sources**
- [docs/troubleshooting.md:13-20](file://docs/troubleshooting.md#L13-L20)

### Missing ADMIN_API_KEY

**Problem**: The system fails with "ADMIN_API_KEY is not set" error.

**Diagnosis Steps**:
1. Locate the .env configuration file
2. Verify ADMIN_API_KEY variable presence
3. Check for proper variable assignment

**Solution**: Edit the .env file to include a properly formatted ADMIN_API_KEY value. Ensure the variable is not empty and follows the expected format.

**Section sources**
- [docs/troubleshooting.md:23-26](file://docs/troubleshooting.md#L23-L26)

## Docker and Container Problems

### Infrastructure Service Failures

**Problem**: Qdrant, MinIO, or PostgreSQL containers fail to start properly.

**Affected Services**: Qdrant (vector database), MinIO (object storage), PostgreSQL (relational database)

**Diagnosis Steps**:
1. Verify Docker daemon status
2. Check port availability for each service
3. Review container health checks
4. Examine Docker logs for detailed error messages

**Port Conflict Commands**:
```bash
lsof -i :6333   # Qdrant
lsof -i :9000   # MinIO
lsof -i :5432   # PostgreSQL
```

**Solution**: 
1. Stop conflicting applications using the identified ports
2. Restart Docker Compose with updated configuration
3. Monitor service health using Docker Compose logs

**Section sources**
- [docs/troubleshooting.md:29-45](file://docs/troubleshooting.md#L29-L45)

### Linux Host Resolution Issues

**Problem**: "host.docker.internal" hostname resolution failures on Linux systems.

**Diagnosis Steps**:
1. Verify Docker version compatibility (20.10+ required)
2. Check network configuration
3. Test hostname resolution within containers

**Solution**: The system automatically configures `extra_hosts` in Docker Compose. If issues persist, update Docker to the minimum required version or manually configure host networking.

**Section sources**
- [docs/troubleshooting.md:97-100](file://docs/troubleshooting.md#L97-L100)

## Port Conflicts

### Admin Panel Port Conflicts

**Problem**: Port 8000 already occupied by another process.

**Impact**: Admin interface fails to start or becomes inaccessible.

**Diagnosis Steps**:
1. Identify process using port 8000
2. Check for existing admin service instances
3. Verify Docker container status

**Solution**: Configure alternative port using environment variables:
```bash
ADMIN_PORT=8080 bash scripts/run_admin.sh
```

**Section sources**
- [docs/troubleshooting.md:60-69](file://docs/troubleshooting.md#L60-L69)

### RAG Service Port Conflicts

**Problem**: RAG service fails to start due to port 8001 conflict.

**Impact**: Document processing and QA functionality unavailable.

**Diagnosis Steps**:
1. Identify process occupying port 8001
2. Check for multiple RAG service instances
3. Verify service dependencies

**Conflict Detection Command**:
```bash
lsof -i :8001
```

**Solution**: Either stop the conflicting process or reconfigure the RAG service:
```bash
RAG_SERVICE_PORT=9001
RAG_SERVICE_URL=http://localhost:9001
```

**Section sources**
- [docs/troubleshooting.md:72-86](file://docs/troubleshooting.md#L72-L86)

## Model Loading and Performance Issues

### Ollama Installation Problems

**Problem**: "Ollama is not installed" error during service startup.

**Diagnosis Steps**:
1. Verify Ollama binary availability
2. Check Ollama service status
3. Confirm model download completion

**Solution**: Download and install Ollama from the official website. Allow sufficient time for initial model downloads (4-6 GB total).

**Section sources**
- [docs/troubleshooting.md:48-51](file://docs/troubleshooting.md#L48-L51)

### llama.cpp Server Issues

**Problem**: "llama-server not found" or port conflicts with llama.cpp services.

**Affected Ports**: 8080 (LLM server), 8090 (embedding server)

**Diagnosis Steps**:
1. Verify llama-server installation
2. Check port availability for both services
3. Confirm model files existence in models/ directory
4. Review service logs in /tmp/llama_*.log

**Verification Commands**:
```bash
llama-server --version
lsof -i :8080   # LLM server
lsof -i :8090   # Embedding server
ls -lh models/  # Model files check
```

**Section sources**
- [docs/troubleshooting.md:103-117](file://docs/troubleshooting.md#L103-L117)

## VK Bot Integration Problems

**Problem**: VK bot not responding in community groups despite proper configuration.

**Diagnosis Checklist**:
1. Verify VK_ACCESS_TOKEN and VK_GROUP_ID in .env configuration
2. Check bot container health status
3. Confirm VK community message settings are enabled
4. Review bot-specific error logs

**Monitoring Commands**:
```bash
docker compose logs -f vk_bot
```

**Additional Configuration Notes**:
- Ensure bot has proper permissions for the target group
- Verify webhook configurations if applicable
- Check rate limiting and API quotas

**Section sources**
- [docs/troubleshooting.md:89-94](file://docs/troubleshooting.md#L89-L94)

## Local Development Environment

### Python Environment Setup

**Problem**: Development environment inconsistencies or missing dependencies.

**Diagnosis Steps**:
1. Verify Python 3.13+ installation
2. Check uv package manager status
3. Confirm workspace member installations

**Environment Configuration**:
The project uses uv workspace management with specific Python version requirements and dependency overrides for platform-specific packages.

**Section sources**
- [pyproject.toml:1-72](file://pyproject.toml#L1-L72)

### Script Execution Issues

**Problem**: Custom deployment scripts failing or not executing properly.

**Diagnosis Steps**:
1. Verify script permissions and executability
2. Check environment variable propagation
3. Confirm dependency availability

**Available Deployment Scripts**:
- `scripts/run_all.sh`: Complete system startup
- `scripts/run_admin.sh`: Admin interface deployment
- `scripts/run_llama_embeddings.sh`: Llama embedding service
- `scripts/run_llama_llm.sh`: Llama language model service
- `scripts/run_ollama_llm.sh`: Ollama language model service

**Section sources**
- [scripts/run_admin.sh](file://scripts/run_admin.sh)
- [scripts/run_all.sh](file://scripts/run_all.sh)
- [scripts/run_llama_embeddings.sh](file://scripts/run_llama_embeddings.sh)
- [scripts/run_llama_llm.sh](file://scripts/run_llama_llm.sh)
- [scripts/run_ollama_llm.sh](file://scripts/run_ollama_llm.sh)

## Advanced Troubleshooting

### Health Check Monitoring

**Problem**: Services appear down but manual verification shows they're running.

**Diagnosis Approach**:
1. Monitor Docker Compose health checks
2. Check individual service health endpoints
3. Verify inter-service communication

**Health Check Configuration**:
- Qdrant: Health endpoint on port 6333
- MinIO: Ready state monitoring
- PostgreSQL: Database connectivity checks
- RAG Service: HTTP health endpoint
- Admin Service: Application-level health checks

**Section sources**
- [docker-compose.yml:11-16](file://docker-compose.yml#L11-L16)
- [docker-compose.yml:30-35](file://docker-compose.yml#L30-L35)
- [docker-compose.yml:49-54](file://docker-compose.yml#L49-L54)
- [docker-compose.yml:83-88](file://docker-compose.yml#L83-L88)

### Configuration Validation

**Problem**: Runtime configuration errors or service misconfigurations.

**Diagnosis Steps**:
1. Validate environment variable completeness
2. Check service URL configurations
3. Verify credential validity
4. Confirm network accessibility

**Configuration Areas**:
- Database connection strings
- S3/Object storage credentials
- LLM provider endpoints
- Service intercommunication URLs

**Section sources**
- [packages/core/src/cafetera_core/config.py](file://packages/core/src/cafetera_core/config.py)
- [packages/rag_service/src/cafetera_rag_service/config.py](file://packages/rag_service/src/cafetera_rag_service/config.py)
- [packages/admin/src/cafetera_admin/config.py](file://packages/admin/src/cafetera_admin/config.py)
- [packages/vk_bot/src/cafetera_vk_bot/config.py](file://packages/vk_bot/src/cafetera_vk_bot/config.py)

## Preventive Measures

### System Maintenance

**Recommended Practices**:
1. Regular Docker volume cleanup
2. Log rotation and monitoring
3. Dependency updates and security patches
4. Performance baseline establishment
5. Backup verification procedures

### Monitoring Setup

**Essential Metrics to Track**:
- Container resource utilization
- Database connection pool status
- Storage capacity and performance
- Network latency between services
- Error rates and response times

### Backup and Recovery

**Critical Data Protection**:
- Database backups with retention policies
- Vector database snapshot scheduling
- Configuration version control
- Access credential rotation schedules

## When to Seek Additional Help

### Escalation Criteria

**Issues Requiring Expert Assistance**:
1. Persistent container startup failures after basic troubleshooting
2. Performance degradation beyond configuration limits
3. Data corruption or loss scenarios
4. Security vulnerabilities or unauthorized access attempts
5. Complex network topology or firewall configuration issues

### Support Resources

**Available Documentation and Community Support**:
- Official Docker documentation and forums
- Python ecosystem support channels
- VK API integration documentation
- Vector database and storage system documentation
- Cloud provider-specific networking guides

### Professional Support Options

**Enterprise Considerations**:
- Production environment monitoring solutions
- Automated alerting and incident response
- Disaster recovery and business continuity planning
- Performance tuning and optimization services
- Security audit and compliance assistance