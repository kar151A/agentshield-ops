# AgentShield Ops — Product Charter

## 1. Product Vision

AgentShield Ops is a secure autonomous incident-response SaaS for companies operating cloud applications and AI agents.

It detects operational and security incidents, investigates probable causes, proposes recovery actions, evaluates risk, requests human approval for sensitive actions, performs controlled recovery and creates tamper-evident audit evidence.

## 2. Target Customer

Our first target customer is a small or medium-sized SaaS company that:

- Runs applications using Kubernetes or cloud infrastructure
- Uses AI agents or automated operational tools
- Has a small DevOps or Site Reliability Engineering team
- Cannot maintain a 24/7 security operations team
- Requires human approval before high-risk infrastructure changes
- Needs evidence for security reviews and compliance audits

## 3. Customer Problem

Production incidents require engineers to manually inspect alerts, logs, metrics and recent deployments.

This process is slow and produces several risks:

- Important evidence may be missed
- Recovery decisions depend on individual experience
- Engineers may perform unsafe commands under pressure
- Actions may be executed without proper approval
- Audit evidence is distributed across multiple systems
- AI agents may call tools with excessive permissions

AgentShield Ops combines investigation, policy enforcement, approval, recovery and evidence collection into one controlled workflow.

## 4. Primary Users

### Operator

Investigates incidents, reviews agent findings and monitors recovery.

### Approver

Reviews proposed high-risk actions and approves or rejects them.

### Security Administrator

Creates policies, manages permissions and reviews security evidence.

### Auditor

Views or exports authorized compliance and incident evidence.

## 5. Initial Demo Scenarios
### Shared Workflow and Execution Boundary

Both scenarios use the same controlled pipeline:

1. Receive the alert
2. Validate and normalize the alert
3. Store the incident
4. Display it on the dashboard
5. Investigate available evidence
6. Propose a recovery action
7. Simulate the proposed action
8. Evaluate deterministic policy and risk
9. Request human approval
10. Execute through a restricted adapter
11. Verify the result
12. Record audit evidence

A proposed action is a recommendation and is not automatically an executed action.

During the 30-day MVP, all execution must use mock adapters or a controlled local Kubernetes cluster. AgentShield will not connect to customer production infrastructure.

### Scenario One: Failed Kubernetes Deployment

A new deployment causes unhealthy pods and increased application errors.
#### Concrete MVP Test Case

| Field | Test value |
|---|---|
| Service | `payments-api` |
| Environment | `development` |
| Alert source | `mock_kubernetes_alert_generator` |
| Incident type | `deployment_failure` |
| Severity | `high` |
| Initial status | `open` |
| Healthy replicas | `0` |
| Expected replicas | `3` |
| Error rate | `38.5%` |
| Suspected deployment | `payments-api-v2` |

#### Proposed Action

The agent proposes `rollback_deployment` for `payments-api`, replacing `payments-api-v2` with the last known healthy version, `payments-api-v1`.

This remains a proposal until the simulation, deterministic policy check and authorized human approval are complete.

#### Verification Conditions

The recovery is successful only when:

- Healthy replicas reach `3/3`
- Error rate falls below `2%`
- Health remains stable for two consecutive verification checks
- No unauthorized execution occurs
- Repeated requests do not execute the rollback twice

AgentShield Ops will:

1. Receive the incident alert
2. Analyze logs, metrics and deployment history
3. Identify the new deployment as the probable cause
4. Recommend a rollback
5. Simulate the proposed rollback
6. Calculate risk and evaluate policy
7. Request human approval
8. Execute an approved mock or local-cluster rollback
9. Verify service recovery
10. Record the complete audit trail

### Scenario Two: Suspicious Traffic

A service receives repeated suspicious requests from an IP address.
#### Concrete MVP Test Case

| Field | Test value |
|---|---|
| Service | `payments-api` |
| Environment | `development` |
| Alert source | `mock_security_alert_generator` |
| Incident type | `suspicious_traffic` |
| Severity | `medium` |
| Initial status | `open` |
| Source IP | `203.0.113.42` |
| Requests per minute | `850` |
| Failed requests | `91%` |

The IP address `203.0.113.42` is reserved for documentation and testing. It does not represent a real customer or attacker.

#### Proposed Action

The agent proposes `block_ip` for `203.0.113.42` in the development environment for 15 minutes.

This remains a proposal until the simulation, deterministic policy check and authorized human approval are complete.

#### Verification Conditions

The response is successful only when:

- Requests from the test IP fall to zero during the next simulated interval
- Normal test traffic remains available
- The temporary block expires after 15 minutes
- No unauthorized block occurs
- Repeated requests do not create duplicate blocks
AgentShield Ops will:

1. Detect abnormal traffic
2. Identify the suspicious source
3. Collect supporting evidence
4. Recommend a temporary IP block
5. Simulate the effect of the block
6. Evaluate the security policy
7. Request human approval
8. Execute an approved mock firewall action
9. Verify that suspicious traffic decreases
10. Produce compliance evidence
### Week One Scope Boundary

Week One is limited to:

1. Receive a mock alert
2. Validate its required fields
3. Normalize it into the shared incident structure
4. Store it for the correct tenant
5. Display it on the operations dashboard

Week One does not include LLM investigation, automated recommendations, policy decisions, human approvals or recovery execution. Those capabilities will be added only after incident ingestion and tenant isolation work correctly.
## 6. Security Principles

AgentShield Ops will follow these principles:

- Deny access by default
- Use least-privilege permissions
- Isolate every tenant's data
- Never expose secrets to the language model
- Treat logs and external content as untrusted input
- Require human approval for high-risk actions
- Make execution tokens short-lived and single-use
- Record every policy decision and action
- Provide an emergency kill switch
- Prevent duplicate execution through idempotency

## 7. MVP Features

The 30-day MVP will include:

- Organization signup and login
- Multi-tenant data isolation
- Role-based access control
- Incident ingestion
- Incident dashboard and timeline
- Multiple specialized AI agents
- Structured root-cause analysis
- Action simulation
- Deterministic policy evaluation
- Risk scoring
- Human approval workflow
- Controlled recovery adapters
- Recovery verification
- Tamper-evident audit history
- Compliance evidence export
- Usage metering and plan limits
- Python SDK and API documentation
- Hosted commercial beta

## 8. Out of Scope for Month One

The first version will not include:

- Unrestricted access to real production infrastructure
- Fully autonomous execution of critical actions
- Formal SOC 2, ISO 27001 or GDPR certification
- Support for every cloud provider
- Custom model training
- Native mobile applications
- Enterprise single sign-on
- Guaranteed production service-level agreements

These may be added after validating the beta with design partners.

## 9. Success Metrics

The MVP is successful when:

- Both demo incidents work from alert to verified recovery
- High-risk actions cannot execute without authorization
- Cross-tenant access tests fail safely
- Every action produces traceable audit evidence
- Duplicate requests do not create duplicate actions
- A new developer can integrate using the SDK in under 30 minutes
- The hosted demo can be reproduced from a clean environment
- At least three potential design partners review the product
- At least one company expresses interest in a pilot

## 10. Ownership

### Karthik

Owns:

- Authentication and authorization
- Tenant isolation
- Security gateway
- Policy and risk engine
- Human approvals
- Compliance evidence
- Audit integrity
- Usage plans and billing controls

### Meganshu

Owns:

- Agent orchestration
- Incident intelligence
- Root-cause investigation
- Action simulation
- Recovery and verification
- Dashboard experience
- Observability
- Deployment infrastructure

### Shared Responsibility

Both developers own:

- API contracts
- Integration reviews
- Automated testing
- Documentation
- Deployment
- Customer demonstrations
- Pilot preparation

## 11. Shared Definition of Done

A feature is complete only when:

- The code has been reviewed
- Automated checks pass
- Authorization boundaries are tested
- Failure behaviour is visible
- Documentation is updated
- The result can be demonstrated from a clean environment