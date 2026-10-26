# AgentShield Ops Control API

FastAPI-based control plane for AgentShield Ops.

## Responsibilities

The API will provide:

- Authentication and authorization
- Tenant-aware request handling
- Incident ingestion
- Policy and risk evaluation
- Human-approval workflows
- Audit and compliance records
- Agent-workflow coordination

## Requirements

- Python 3.12
- A project virtual environment

## Local Setup

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r apps\api\requirements.txt