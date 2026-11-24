# Ossiemate AI Lab - Infrastructure Baseline

## 1. Project Overview

Project: Ossiemate AI Lab
Environment: Development
Baseline Date: 25 November 2026
Repository: careerossiemate/ossiemate-ai-lab
Framework: Microsoft Foundry and AI-103
Backend Version: 0.1.0

### Objectives

- Demonstrate practical AI business solutions.
- Execute AI workloads entirely in Azure.
- Maintain a permanent public showcase portal.
- Restrict live AI execution to authorised users.
- Preserve application data independently of compute.
- Enable automated runtime deployment and deletion.
- Minimise ongoing cloud infrastructure costs.

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Frontend Build | Node.js, esbuild |
| Authentication | Microsoft Entra ID, MSAL |
| Backend | Python 3.12, FastAPI |
| AI Integration | OpenAI SDK, Responses API |
| AI Platform | Microsoft Foundry |
| AI Model | GPT-5.2 |
| Compute | Azure Container Apps |
| File Storage | Azure Blob Storage |
| Structured Storage | Azure Table Storage |
| Container Registry | Azure Container Registry |
| Cloud Authentication | User-assigned Managed Identity |
| Source Control | GitHub |
| Frontend CI/CD | GitHub Actions |
| Infrastructure Automation | Bicep - Planned |

## 3. Azure Resource Inventory

| Resource Group | Resource | Region |
|---|---|---|
| AI103-LAB-RG | AI103-agent-lab - Foundry account | Australia East |
| AI103-LAB-RG | AI103-agent-lab - Foundry project | Australia East |
| rg-ai103-showcase | swa-ossiemate-ailab | East Asia |
| rg-ai103-persistent | stossiemateailab | Australia East |
| rg-ai103-persistent | acrossiemateailab | Australia East |
| rg-ai103-persistent | id-ai103-lab | Australia East |
| rg-ai103-runtime | cae-ai103-lab | Australia East |
| rg-ai103-runtime | ca-ai103-backend | Australia East |

## 4. Application Architecture

Public User
    |
Azure Static Web Apps
    |
Microsoft Entra ID Authentication
    |
FastAPI Backend - Azure Container Apps
    |
User-assigned Managed Identity
    |
    +-- Microsoft Foundry
    +-- Azure Blob Storage
    +-- Azure Table Storage

GitHub Actions currently builds and deploys the frontend.
Azure Container Registry stores backend container images.

Automated backend deployment and deletion are planned.

## 5. Frontend Configuration

Application: swa-ossiemate-ailab
Pricing Tier: Free
Deployment Branch: develop

URL:
https://mango-sea-0589cd400.6.azurestaticapps.net

Public capabilities:

- AI solution catalogue
- Exercise demonstration pages
- Architecture overview
- Application availability information

Authorised capabilities:

- Infrastructure diagnostics
- Learning progress management
- Live AI demonstrations - Planned

## 6. Backend Configuration

Application: ca-ai103-backend
Environment: cae-ai103-lab
Workload Profile: Consumption
Python Version: 3.12.16
CPU: 0.5 vCPU
Memory: 1 GiB
Minimum Replicas: 0
Maximum Replicas: 1
Target Port: 8000
External Ingress: Enabled
Insecure Ingress: Disabled
Revision Mode: Single
Persistent Log Destination: None

Baseline Revision:
ca-ai103-backend--9l1axkl

Backend URL:
https://ca-ai103-backend.wittywave-5f5679ff.australiaeast.azurecontainerapps.io

The backend URL may change when the runtime environment
is deleted and recreated.

## 7. Container Registry

Registry: acrossiemateailab
Pricing Tier: Basic
Admin Account: Disabled
Repository: ai103-backend

Image Version: 0.1.0

Baseline Image Digest:

sha256:c5bbd24c2655ed6e9f312c4bddf04c888abb83978af106386ef416160e39a18a

Container images are retained independently of runtime
infrastructure.

## 8. Identity and Security

Managed Identity: id-ai103-lab

Azure RBAC assignments:

| Resource | Role |
|---|---|
| Container Registry | AcrPull |
| Storage Account | Storage Blob Data Contributor |
| Storage Account | Storage Table Data Contributor |
| Foundry Account | Cognitive Services OpenAI User |

Application security controls:

- Microsoft Entra ID authentication
- Single-tenant application registrations
- JWT signature and claim validation
- API audience and issuer validation
- Delegated API scope validation
- Authorised user allowlist
- HTTPS-only application access
- Restricted CORS configuration
- Passwordless Azure resource authentication
- Non-root container execution
- Immutable container image deployment

No API keys, passwords or access tokens are included
in this document.

## 9. Persistent Storage

Storage Account: stossiemateailab
Account Type: StorageV2
Redundancy: Standard LRS
Default Access Tier: Hot
Public Blob Access: Disabled
Shared Key Access: Disabled

### Blob Containers

| Container | Purpose |
|---|---|
| backups | Application state and backup files |
| brochures | Document search datasets |
| demonstration-results | AI outputs and execution results |
| lab-config | Application configuration |
| training-data | Fine-tuning datasets |

### Azure Tables

| Table | Purpose |
|---|---|
| ConversationHistory | Conversation records |
| ExecutionMetrics | AI execution metrics |
| ExerciseProgress | Learning progress |
| LabConfiguration | Application settings |
| TrainingJobs | Fine-tuning job tracking |

## 10. Shared Backend Modules

| Module | Responsibility |
|---|---|
| shared/config.py | Environment configuration |
| shared/auth.py | Managed Identity authentication |
| shared/foundry_client.py | AI inference integration |
| shared/blob_storage.py | File storage operations |
| shared/table_storage.py | Structured data operations |
| shared/user_auth.py | Access token validation |
| shared/user_authorization.py | User allowlist validation |
| routers/protected.py | Protected application endpoints |
| main.py | FastAPI application |

## 11. Implemented API Endpoints

### Public Endpoints

GET /
GET /health
GET /api/info
GET /api/exercises

### Protected Endpoints

GET /api/auth/me
GET /api/diagnostics
GET /api/progress
POST /api/progress

Exercise-specific AI endpoints are planned.

## 12. Infrastructure Validation Results

| Validation | Result |
|---|---|
| Azure resource inventory | Passed - 8 resources |
| Container image cloud build | Passed |
| Container deployment | Passed |
| Backend health endpoint | Passed |
| Frontend deployment | Passed |
| Microsoft Entra sign-in | Passed |
| Microsoft Entra sign-out | Passed |
| Authorised user access | Passed |
| Missing token rejection | Passed |
| Invalid token rejection | Passed |
| CORS allowed origin | Passed |
| CORS unapproved origin | Passed |
| Managed Identity token acquisition | Passed |
| Blob Storage connectivity | Passed |
| Blob Storage upload | Passed |
| Blob Storage download | Passed |
| JSON content validation | Passed |
| Blob existence and listing | Passed |
| Blob metadata validation | Passed |
| Blob deletion | Passed |
| Blob cleanup verification | Passed |
| Table Storage connectivity | Passed |
| Exercise progress creation | Passed |
| Exercise progress update | Passed |
| Exercise progress retrieval | Passed |
| Foundry inference | Passed |

### Blob Storage Test

File Format: JSON
Uploaded Size: 239 bytes
Downloaded Size: 239 bytes
Content Type: application/json
Access Tier: Hot
Content Validation: Passed
Metadata Validation: Passed
Deletion: Passed
Active Blob Existence After Deletion: False
Matching Active Files After Deletion: 0

### Table Storage Test

Exercise: 03
Status: in_progress
Recorded Completion: 60 percent

This is internal showcase progress, not an official
Microsoft certification completion percentage.

### Foundry Inference Test

Model: GPT-5.2
Authentication: Managed Identity
API: Responses API
Status: Completed

Prompt:
Reply with exactly: Ossiemate AI Lab is connected.

Actual Response:
Ossiemate AI Lab is connected.

Execution Time: 81.994 seconds
Input Tokens: 30
Output Tokens: 13
Total Tokens: 43
Output Token Limit: 256
Response Storage: Disabled

Functional Validation: Passed

Performance Observation:
The response latency was unusually high for a small request.
Root cause has not yet been established.

## 13. Git Branch Strategy

| Branch | Purpose |
|---|---|
| develop | Development and testing |
| preprod | Integration and release validation |
| main | Production baseline |

Frontend CI/CD is implemented for develop.
Preproduction and production deployment workflows are planned.

## 14. Cost Management

Implemented controls:

- Azure Static Web Apps Free tier.
- Consumption-based backend compute.
- Minimum replica count of zero.
- Maximum replica count of one.
- Small backend CPU and memory allocation.
- No persistent application log destination.
- Reusable container images.
- Standard LRS storage.

Planned controls:

- One-click runtime deployment and deletion.
- AI output token limits across exercise endpoints.
- Request rate limiting and usage quotas.
- AI token consumption monitoring.
- Lower-cost model selection where appropriate.
- Budget monitoring and alerts.

Container Registry, storage, AI inference and other
billable services may continue to incur charges.

## 15. Runtime Lifecycle Strategy

Retained resource groups:

- AI103-LAB-RG
- rg-ai103-showcase
- rg-ai103-persistent

Temporary runtime resource group:

- rg-ai103-runtime

Planned shutdown process:

1. Confirm persistent data is saved.
2. Delete designated runtime resources.
3. Retain frontend, storage, registry and identity.
4. Keep the public showcase accessible.

Planned startup process:

1. Recreate the Container Apps environment.
2. Deploy the approved container image.
3. Attach the existing Managed Identity.
4. Restore environment configuration.
5. Discover the backend URL.
6. Update frontend runtime configuration.
7. Validate application health and authentication.
8. Retrieve persistent application state.

This lifecycle has not yet been automated or tested.

## 16. Outstanding Technical Activities

- Integrate Exercise 03 conversational AI.
- Integrate Exercise 04 file search and web search.
- Integrate Exercise 05 fine-tuning demonstrations.
- Integrate Exercise 06 responsible AI demonstrations.
- Investigate Foundry inference latency.
- Implement AI request limits and usage controls.
- Validate conversation ownership and isolation.
- Test valid non-allowlisted user rejection.
- Update Foundry diagnostic status in the portal.
- Independently test Blob Storage overwrite operations.
- Measure actual scale-to-zero behaviour.
- Implement Bicep infrastructure templates.
- Implement automated runtime deployment.
- Implement automated runtime deletion.
- Test persistence across runtime recreation.
- Implement preproduction and production CI/CD.
- Configure a custom domain.
- Review fine-tuning availability and costs before execution.

## 17. Baseline Conclusion

The shared cloud infrastructure is deployed.

Core authentication, storage and AI inference capabilities
have been functionally validated.

The infrastructure is ready for controlled exercise
integration in the development environment.

Production readiness, automated runtime restoration and
complete application security testing remain outstanding.