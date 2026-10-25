# ADR 0001: Core Technology Stack

- Status: Accepted
- Date: 2026-10-25
- Decision owners: Karthik and Meganshu

## Context

AgentShield Ops must deliver a secure multi-tenant autonomous incident-response SaaS beta within 30 days.

The stack must support:

- Stateful AI-agent workflows
- Deterministic security controls
- Human approval
- Multi-tenant isolation
- Background processing
- Auditability
- Fast full-stack development
- Future commercial scaling

## Decision 1: FastAPI for the Control API

### Selected

Python, FastAPI and Pydantic.

### Alternatives considered

- Django with Django REST Framework
- Node.js with NestJS
- Express.js

### Reason

FastAPI provides:

- Native integration with Python AI libraries
- Automatic OpenAPI documentation
- Strong Pydantic validation
- Async endpoint support
- Low development overhead
- Easy structured-output validation

Django provides more built-in features but adds unnecessary framework weight for the initial API-focused MVP.

NestJS provides strong TypeScript architecture, but using Python for both the API and agent services reduces cross-language integration work during the 30-day build.

### Consequence

The backend team must enforce clear modules and dependency boundaries because FastAPI does not impose as much structure as Django or NestJS.

## Decision 2: PostgreSQL as the Primary Database

### Selected

PostgreSQL.

### Alternatives considered

- MongoDB
- MySQL
- Firebase

### Reason

AgentShield contains strongly related security records:

- Tenants
- Users
- Roles
- Incidents
- Policies
- Approvals
- Executions
- Audit events

PostgreSQL provides:

- ACID transactions
- Foreign-key constraints
- Row-Level Security
- JSONB for flexible evidence
- Mature indexing
- Reliable audit and approval state

MongoDB offers flexible documents but does not provide the same relational integrity needed for sensitive approval and execution workflows.

### Consequence

Schema migrations must be reviewed carefully, and every tenant-owned table must include an organization identifier.

## Decision 3: LangGraph for Agent Orchestration

### Selected

LangGraph.

### Alternatives considered

- A custom while-loop agent
- CrewAI
- AutoGen
- A traditional workflow engine

### Reason

AgentShield needs an explicit state machine that can:

- Pause for human approval
- Resume without repeating side effects
- Persist workflow state
- Route failures safely
- Make transitions visible
- Support deterministic checkpoints

A free-running agent loop would be difficult to test and audit.

CrewAI is useful for role-based agent collaboration, but AgentShield requires strict workflow state and controlled transitions rather than open-ended agent conversations.

A traditional workflow engine is reliable but may require additional integration to support model calls and agent state within the one-month schedule.

### Consequence

Every LangGraph node must have structured input and output. Security decisions must remain outside the model-driven graph nodes.

## Decision 4: Next.js for the Dashboard

### Selected

Next.js with TypeScript and Tailwind CSS.

### Alternatives considered

- React with Vite
- Angular
- Vue
- Server-rendered Python templates

### Reason

Next.js provides:

- File-based routing
- Layouts
- TypeScript support
- Server and client components
- Production deployment options
- A strong React ecosystem
- Fast development of SaaS dashboards

React with Vite is simpler but would require additional routing and application conventions.

Angular provides stronger built-in structure but has greater learning and implementation overhead for this one-month project.

### Consequence

Backend authorization remains mandatory. Next.js route protection and hidden UI elements are not sufficient security controls.

## Decision 5: Redis for Temporary State and Queues

### Selected

Redis with a Python background-job system.

### Alternatives considered

- RabbitMQ
- Kafka
- Running all work inside API requests

### Reason

Redis provides:

- Low-latency queue operations
- Short-lived caching
- Rate-limit counters
- Distributed locks
- Idempotency support
- Simple local Docker setup

RabbitMQ provides stronger dedicated messaging features but adds operational complexity.

Kafka is valuable for large event-streaming platforms but is excessive for the initial workload and 30-day beta.

Long-running agent workflows must not execute inside HTTP request processes because requests can time out or be interrupted.

### Consequence

Redis is not the permanent system of record. Durable workflow results must be stored in PostgreSQL.

## Decision 6: Model-Provider Abstraction

### Selected

A common internal interface supporting mock responses and replaceable external models.

### Alternatives considered

- Direct calls to one model provider throughout the code
- Hosting a large local model immediately
- Selecting models separately inside every agent

### Reason

A provider abstraction gives us:

- Vendor independence
- Easier model comparison
- Deterministic mocked tests
- Centralized retries and timeouts
- Centralized token and cost tracking
- Easier privacy controls
- The ability to select models by task

We will begin with mock responses. A real model will be introduced only after orchestration, validation and approval boundaries work correctly.

### Consequence

All models must return validated structured output. Provider-specific response objects cannot leak into agent business logic.

## Decision 7: Open Policy Agent Behind a Policy Interface

### Selected

A policy interface with deterministic local rules first and Open Policy Agent integration after the basic workflow works.

### Alternatives considered

- Letting the LLM decide permissions
- Hard-coding authorization throughout API endpoints
- Building a completely custom policy language

### Reason

Security decisions must be deterministic, explainable and testable.

Open Policy Agent supports policy-as-code and separates policy decisions from application logic. However, introducing Rego immediately may slow early development.

Therefore:

1. Define the policy interface first.
2. Implement a small deterministic Python version.
3. Integrate Open Policy Agent without changing callers.

The LLM will never be the final authority for access or execution.

### Consequence

Every policy decision must record its policy identifier, version, inputs, result and explanation.

## Final Decision

The initial stack is:

- Frontend: Next.js, TypeScript and Tailwind CSS
- Control API: FastAPI, Python and Pydantic
- Database: PostgreSQL
- Queue and temporary state: Redis
- Agent orchestration: LangGraph
- Policy enforcement: Policy interface followed by Open Policy Agent
- Local development: Docker Compose
- Testing: Pytest and Playwright
- Model integration: Provider-independent interface with mocks first

This stack is accepted for the 30-day beta. Changes require another ADR.