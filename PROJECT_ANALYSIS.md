# MiniStack — Detailed Project Analysis Report

**Date:** 2026-04-12  
**Version Analyzed:** 1.2.5  
**License:** MIT  
**Repository:** https://github.com/ministackorg/ministack

---

## 1. Executive Summary

**MiniStack** is a free, open-source local AWS emulator designed as a drop-in replacement for LocalStack. It emulates **41 AWS services** on a single port (default `4566`) and is compatible with `boto3`, AWS CLI, Terraform, CDK, Pulumi, and any AWS SDK. Key differentiators include a ~200MB Docker image (~30MB RAM at idle vs LocalStack's ~1GB/~500MB RAM), fast startup under 2 seconds, real infrastructure support (RDS, ElastiCache, Athena via DuckDB, ECS), and multi-tenancy via 12-digit numeric AWS access keys.

---

## 2. Technology Summary Table

| Category | Technology | Version / Details | Purpose |
|----------|-----------|-------------------|---------|
| **Language** | Python | 3.10, 3.11, 3.12 | Primary programming language |
| **Language** | JavaScript/Node.js | Runtime support | Lambda function execution (Node.js handlers) |
| **Language** | Go | Testcontainers integration | Go testcontainers support |
| **Language** | Java | Testcontainers integration | Java testcontainers support |
| **Web Server** | Uvicorn (ASGI) | ≥0.30.6 | Single-port HTTP server |
| **HTTP Parsing** | httptools | ≥0.6.1 | High-performance HTTP parsing |
| **Serialization** | PyYAML | ≥6.0 | CloudFormation template parsing |
| **Security** | defusedxml | ≥0.7 | Safe XML parsing (prevents XXE attacks) |
| **Database** | DuckDB | ≥0.10.0 (optional) | Athena SQL query emulation |
| **Database** | Redis | 7 (Docker) | ElastiCache emulation backend |
| **Containerization** | Docker SDK | ≥7.0.0 (optional) | Lambda Docker RIE, RDS, ElastiCache, ECS |
| **Crypto** | cryptography | ≥41.0 (optional) | ACM certificate generation, KMS operations |
| **DB Drivers** | psycopg2-binary | ≥2.9 (optional) | RDS PostgreSQL emulation |
| **DB Drivers** | PyMySQL | ≥1.1 (optional) | RDS MySQL emulation |
| **Data Format** | cbor2 | ≥5.4.0 | CBOR encoding for smithy-rpc-v2 |
| **Testing** | pytest | ≥8.0 | Test framework |
| **Testing** | pytest-xdist | ≥3.6 | Parallel test execution |
| **Testing** | pytest-cov | ≥5.0 | Code coverage |
| **AWS SDK** | boto3 | ≥1.34 (dev) | Test client library |
| **Linting** | ruff | ≥0.4 | Code linting and formatting |
| **Build System** | setuptools | ≥68 | Python package building |
| **Containerization** | Docker | Alpine-based images | Containerized deployment |
| **Orchestration** | Docker Compose | 3.8 | Multi-service deployment (with Redis) |
| **CI/CD** | GitHub Actions | — | Automated testing, PyPI & Docker publishing |

---

## 3. Implemented Features Summary

| Feature | Description | Services/Modules |
|---------|-------------|------------------|
| **S3 Emulation** | Full S3 API: buckets, objects, multipart uploads, versioning, tagging, object lock, replication, lifecycle, CORS, ACL, policy, notifications, range requests, virtual-hosted and path-style addressing | `s3.py`, `s3files.py` |
| **SQS Emulation** | Queue CRUD, send/receive/delete messages, batch operations, visibility timeouts, dead-letter queues, FIFO queues, message attributes, tagging | `sqs.py` |
| **SNS Emulation** | Topic CRUD, publish/subscribe, email/SMS/HTTP/SQS/Lambda endpoints, platform applications, message attributes, batching | `sns.py` |
| **DynamoDB Emulation** | Table CRUD, item CRUD, Query, Scan, BatchWrite, BatchGet, TransactWrite, TransactGet, GSI/LSI, streams, TTL, PITR, expression evaluation | `dynamodb.py` |
| **Lambda Emulation** | Function CRUD, invoke (sync/async), versions, aliases, layers, event source mappings (SQS poller), permissions, function URLs, concurrency, warm worker pool (Python & Node.js), Docker execution mode | `lambda_svc.py`, `lambda_runtime.py` |
| **IAM Emulation** | Roles, users, policies, instance profiles, access keys, policy simulation, attachment/detachment, tagging | `iam_sts.py` |
| **STS Emulation** | GetCallerIdentity, AssumeRole, GetSessionToken, AssumeRoleWithWebIdentity, AssumeRoleWithSAML | `iam_sts.py` |
| **Secrets Manager** | Secret CRUD, versioning, secret string/binary, tagging, rotation (stub) | `secretsmanager.py` |
| **CloudWatch Logs** | Log groups, log streams, put/get/filter log events, retention, tagging | `cloudwatch_logs.py` |
| **CloudWatch Metrics** | PutMetricData, GetMetricData, ListMetrics, alarms (composite, metric), alarm history | `cloudwatch.py` |
| **SSM Parameter Store** | Parameter CRUD (String, StringList, SecureString), get parameters by path, history, tagging | `ssm.py` |
| **EventBridge** | Event bus CRUD, rule CRUD, put events, targets (Lambda invocation), tagging | `eventbridge.py` |
| **Kinesis** | Stream CRUD, shard management, put/get records, shard iterators, enhanced fan-out (stub), tagging | `kinesis.py` |
| **SES / SES v2** | Email sending (SendEmail, SendRawEmail, SendTemplatedEmail), identity verification, configuration sets, templates, v2 REST API | `ses.py`, `ses_v2.py` |
| **ACM** | Certificate request/import, describe, list, delete, export, tagging | `acm.py` |
| **WAF v2** | Web ACL, rules, IP sets, regex pattern sets, logging configuration, tagging | `waf.py` |
| **Step Functions** | State machine CRUD, executions, activity CRUD, ASL interpreter, TestState API, mock config | `stepfunctions.py` |
| **API Gateway v1 & v2** | REST APIs, HTTP APIs, stages, resources, methods, integrations, deployments, API keys, usage plans, execute-api endpoint | `apigateway.py`, `apigateway_v1.py` |
| **ALB/ELBv2** | Load balancer CRUD, target groups (Lambda/instance), listeners, rules, target health, tag management | `alb.py` |
| **KMS** | Key CRUD, encrypt/decrypt, generate data key, aliases, grants, key policies, tagging | `kms.py` |
| **RDS** | DB instance/cluster CRUD, subnet groups, parameter groups, engine versions, snapshots, read replicas, Data API | `rds.py`, `rds_data.py` |
| **ElastiCache** | Cache cluster/replication group CRUD, subnet/parameter groups, snapshots, engine versions | `elasticache.py` |
| **EC2** | Instances, images, security groups, key pairs, VPCs, subnets, route tables, internet gateways, ENIs, VPC endpoints, EBS volumes, tags | `ec2.py` |
| **ECS** | Clusters, task definitions, services, tasks, stop task, container instance management | `ecs.py` |
| **ECR** | Repository CRUD, image push/pull metadata, lifecycle policies, tagging, replication config | `ecr.py` |
| **EFS** | File system CRUD, mount targets, access points, backup, tagging | `efs.py` |
| **CloudFront** | Distribution CRUD, origin access control, invalidations, tagging, cache policies, origin request policies | `cloudfront.py` |
| **CloudFormation** | Stack CRUD, change sets, drift detection, 66+ provisioners, intrinsic functions (Ref, Fn::GetAtt, Fn::Join, Fn::Sub, Fn::If, Fn::And, Fn::Or, Fn::Not), YAML tag support, topological sort, exports/imports | `cloudformation/engine.py`, `cloudformation/provisioners.py`, `cloudformation/stacks.py`, `cloudformation/changesets.py`, `cloudformation/handlers.py`, `cloudformation/helpers.py` |
| **Route 53** | Hosted zones, record sets, health checks, reusable delegation sets, tagging | `route53.py` |
| **Cognito** | User pools, user pool clients, identity pools, groups, users, admin operations, JWKS, OIDC well-known endpoints | `cognito.py` |
| **AppSync** | GraphQL API CRUD, schema, resolvers, data sources, API keys, tagging | `appsync.py` |
| **Athena** | Workgroups, query execution, result retrieval, DuckDB SQL engine, mock config via runtime API | `athena.py` |
| **EMR** | Cluster CRUD, steps, instance groups, security configurations, tagging | `emr.py` |
| **Glue** | Database/table/crawler/job CRUD, ETL execution (Docker sandbox), connections, triggers, classifiers, data catalog | `glue.py` |
| **Firehose** | Delivery stream CRUD, put records, S3/Lambda/Elasticsearch destinations, tagging | `firehose.py` |
| **AutoScaling** | ASG CRUD, launch configurations, scaling policies, lifecycle hooks, scheduled actions, instance management | `autoscaling.py` |
| **CodeBuild** | Project CRUD, batch builds, source credentials, report groups, tagging | `codebuild.py` |
| **Service Discovery** | Namespace CRUD, service CRUD, instance registration/deregistration, discover instances | `servicediscovery.py` |
| **Multi-Tenancy** | 12-digit numeric AWS access keys act as Account IDs; `AccountScopedDict` namespaces all state per account | `responses.py`, `router.py` |
| **State Persistence** | Optional JSON-based state persistence across restarts for all services | `persistence.py` |
| **Admin Endpoints** | `/_ministack/health`, `/_ministack/reset`, `/_ministack/config` for runtime configuration | `app.py` |
| **Init Scripts** | `/docker-entrypoint-initaws.d/` and `/_ready/` script execution on startup | `app.py` |
| **Docker Compose** | Multi-service deployment with Redis dependency, optional Postgres | `docker-compose.yml` |
| **Testcontainers** | Integration support for Python, Go, and Java test frameworks | `Testcontainers/` |

---

## 4. Integration Summary Table

| Integration Type | Target System/Service | Protocol/API | Purpose | Implementation |
|-----------------|----------------------|-------------|---------|----------------|
| **Docker Engine** | Local Docker daemon | Docker Socket (`/var/run/docker.sock`) | Lambda Docker RIE, RDS containers, ElastiCache containers, ECS tasks, Glue ETL sandbox, CloudFormation provisioners | `docker` SDK (`docker_lib`) |
| **Redis** | Redis server | RESP (TCP port 6379) | ElastiCache emulation backend | `REDIS_HOST`/`REDIS_PORT` env vars |
| **DuckDB** | Embedded SQL engine | In-process | Athena query execution | `duckdb` Python package |
| **PostgreSQL** | RDS PostgreSQL | TCP (port 15432+) | RDS DB instance emulation | `psycopg2-binary`, Docker containers |
| **MySQL** | RDS MySQL | TCP (port 15432+) | RDS DB instance emulation | `pymysql`, Docker containers |
| **AWS CLI** | External CLI tool | HTTP (endpoint URL) | Integration testing, `awslocal` wrapper | `bin/awslocal` bash script |
| **boto3** | AWS SDK for Python | HTTP (endpoint URL) | Python client integration, test suite | `tests/conftest.py` |
| **Terraform** | IaC tool | HTTP (endpoint URL) | Infrastructure-as-code testing | Virtual-hosted S3, provider-compatible endpoints |
| **CDK / Pulumi** | IaC frameworks | HTTP (endpoint URL) | Infrastructure-as-code testing | Compatible endpoints |
| **GitHub Actions** | CI/CD platform | — | Automated testing, PyPI & Docker image publishing | `.github/workflows/ci.yml`, `docker-publish.yml`, `pypi-publish.yml` |
| **Testcontainers** | Python/Go/Java test frameworks | Docker API | Containerized testing integration | `Testcontainers/python-testcontainers/`, `go-testcontainers/`, `java-testcontainers/` |
| **LocalStack Compatibility** | Drop-in replacement | Same API surface | Compatible with any LocalStack client | Single-port ASGI on 4566, matching headers/paths |

---

## 5. Directory Analysis

### 5.1 `/mnt/c/Tools/code/ministack-huawei/ministack/`

**Predominant Language:** Python 3.10+

**Main Functionality:** Core application package. Contains the ASGI application entry point (`app.py`), CLI entry point (`__main__.py`), and sub-packages for core infrastructure (`core/`) and AWS service emulators (`services/`).

**Key Files:**
- `app.py` (913 lines) — ASGI application, request routing, CORS handling, admin endpoints, virtual-hosted S3, API Gateway execute-api dispatch, ALB data-plane routing, AWS chunked body decoding, init/ready script execution.
- `__main__.py` — CLI entry point, delegates to `app.main()`.
- `__init__.py` — Empty package marker.

**Security Concerns:**

| # | Vulnerability | Severity | Location | Description | Suggestion |
|---|--------------|----------|----------|-------------|------------|
| 1 | `eval()` usage | **High** | `core/persistence.py:40` | Uses `eval(key_repr)` to deserialize key representations in persisted state. If state files are tampered with, this enables arbitrary code execution. | Replace `eval()` with `ast.literal_eval()` or use a safe serialization format (e.g., JSON arrays for tuple keys). |
| 2 | Wildcard CORS headers | **Medium** | `app.py` (multiple locations) | `Access-Control-Allow-Origin: *`, `Allow-Methods: *`, `Allow-Headers: *` are set on all responses. While acceptable for a local dev tool, it could be a concern if accidentally exposed on a network. | Document the security implication clearly; consider making CORS configurable via environment variable. |
| 3 | Subprocess execution of init/ready scripts | **Medium** | `app.py:710,744,876` | Shell scripts from `/docker-entrypoint-initaws.d/` and `/_ready/` are executed directly. If these volumes are mounted from untrusted sources, arbitrary code execution is possible. | Already mitigated by Docker volume trust model; document the trust boundary clearly. Consider validating script permissions. |
| 4 | No input sanitization on `_ministack/config` endpoint | **Medium** | `app.py:319-336` | While there is a whitelist of allowed config keys, the endpoint uses `setattr()` on module-level variables. If the whitelist is expanded without care, this could be exploited. | Add type validation on values; log all config changes. |

**Improvement Suggestions:**

| # | Suggestion | Impact | Priority |
|---|-----------|--------|----------|
| 1 | Replace `eval()` with `ast.literal_eval()` in persistence.py | **High** — eliminates code injection risk | Immediate |
| 2 | Add request rate limiting to admin endpoints (`/_ministack/reset`, `/_ministack/config`) | **Medium** — prevents accidental state wipe during development | Medium |
| 3 | Add structured logging (JSON format) option for better observability | **Medium** — improves debugging in CI/CD pipelines | Low |
| 4 | Implement `Content-Security-Policy` and `X-Content-Type-Options` headers | **Low** — defense-in-depth for browser-accessed endpoints | Low |

---

### 5.2 `/mnt/c/Tools/code/ministack-huawei/ministack/core/`

**Predominant Language:** Python 3.10+

**Main Functionality:** Core infrastructure layer shared by all service emulators.

**Key Files:**
- `router.py` (320+ lines) — AWS service detection via `X-Amz-Target`, `Authorization` header, `Host` header, URL path patterns, and query parameter action mapping. Extracts region, access key ID, and account ID from requests.
- `responses.py` (200+ lines) — Response formatting utilities: XML/JSON response builders, AWS-style error responses, timestamp utilities, hash utilities, `AccountScopedDict` for multi-tenant state isolation, and per-request account ID management via `contextvars`.
- `persistence.py` (90+ lines) — State persistence layer: saves/loads service state as JSON files, handles `AccountScopedDict` serialization/deserialization, atomic writes via temp files.
- `lambda_runtime.py` (460+ lines) — Lambda warm/cold worker pool: persistent subprocess workers for Python and Node.js runtimes, zip extraction, layer handling with zip-slip validation, JSON-line protocol for worker communication.

**Security Concerns:**

| # | Vulnerability | Severity | Location | Description | Suggestion |
|---|--------------|----------|----------|-------------|------------|
| 1 | `eval()` in `_json_object_hook` | **High** | `persistence.py:40` | Arbitrary code execution via crafted state files. | Replace with `ast.literal_eval()` or store tuple keys as JSON arrays `["account_id", "original_key"]`. |
| 2 | Worker script injection via Lambda config | **Medium** | `lambda_runtime.py` | Lambda environment variables are injected directly into subprocess spawn environment. A crafted `Environment.Variables` config could manipulate subprocess behavior. | Sanitize environment variable values; prefix Lambda env vars with `AWS_LAMBDA_` namespace. |
| 3 | NUL-byte separator in persistence keys | **Low** | `persistence.py:28,38` | Uses `\x00` as separator for serialized `AccountScopedDict` keys. If account IDs or keys ever contain NUL bytes, this breaks. | Use JSON array serialization for compound keys. |

**Improvement Suggestions:**

| # | Suggestion | Impact | Priority |
|---|-----------|--------|----------|
| 1 | Replace `eval()` with `ast.literal_eval()` or JSON array key serialization | **High** — critical security fix | Immediate |
| 2 | Add worker process resource limits (memory, CPU, timeout) in `lambda_runtime.py` | **High** — prevents resource exhaustion from runaway Lambda functions | High |
| 3 | Add timeout enforcement on Lambda worker stderr drain (`_drain_stderr`) | **Medium** — prevents blocking on stalled workers | Medium |
| 4 | Consider using `asyncio.create_subprocess_exec` instead of `subprocess.Popen` for Lambda workers | **Medium** — better integration with ASGI event loop | Low |

---

### 5.3 `/mnt/c/Tools/code/ministack-huawei/ministack/services/`

**Predominant Language:** Python 3.10+

**Main Functionality:** Individual AWS service emulators. 42 Python modules implementing the AWS API surface for each service. Each module follows a consistent pattern:
- Module-level `AccountScopedDict` instances for state storage
- `handle_request(method, path, headers, body, query_params)` async/sync function
- `reset()` function for state cleanup
- `get_state()` / `restore_state(data)` for persistence

**Key Subdirectory:**
- `cloudformation/` (7 files) — CloudFormation engine with YAML/JSON template parsing, intrinsic function resolution (`Ref`, `Fn::GetAtt`, `Fn::Join`, `Fn::Sub`, `Fn::If`, `Fn::And`, `Fn::Or`, `Fn::Not`, `Fn::Select`, `Fn::FindInMap`, `Fn::Base64`, `Fn::ImportValue`), condition evaluation, topological sort for resource creation order, and 66+ provisioners for actual resource creation.

**Notable Large Files:**
- `s3.py` (2,935 lines) — Most complex service: multipart uploads, versioning, object lock, replication, lifecycle, CORS, policy, notifications, range requests, virtual-hosted addressing.
- `lambda_svc.py` (3,062 lines) — Lambda service: function/alias/version/layer management, event source mappings, warm worker pool integration, SQS background poller.
- `dynamodb.py` (1,899 lines) — Full DynamoDB API: streams, TTL, PITR, expression evaluation, transactions.

**Security Concerns:**

| # | Vulnerability | Severity | Location | Description | Suggestion |
|---|--------------|----------|----------|-------------|------------|
| 1 | Subprocess execution in Glue ETL | **Medium** | `glue.py:740` | Glue jobs spawn `subprocess.run()` for ETL execution. If job code is user-controlled, this is intentional but should be documented. | Document the security boundary; consider containerized sandbox for production use. |
| 2 | Hardcoded test credentials in Makefile | **Low** | `Makefile` | `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test` in test target. Acceptable for local testing but could leak if Makefile output is logged. | Use environment variable overrides with sensible defaults. |
| 3 | No input length limits on request bodies | **Low** | Multiple service files | Large request bodies are read into memory without bounds checking. A malicious client could cause memory exhaustion. | Add configurable max body size limit (e.g., 100MB default). |

**Improvement Suggestions:**

| # | Suggestion | Impact | Priority |
|---|-----------|--------|----------|
| 1 | Extract common response/error patterns into a shared base class or mixin | **Medium** — reduces ~8,000+ lines of duplicated response logic across 42 files | High |
| 2 | Add request body size limits across all service handlers | **High** — prevents memory exhaustion | High |
| 3 | Implement pagination consistently across all `List*` operations (some services lack proper pagination tokens) | **Medium** — improves API compatibility with real AWS | Medium |
| 4 | Add type hints to all service handler signatures | **Medium** — improves IDE support and enables static type checking | Medium |
| 5 | Consider splitting very large files (`s3.py`, `lambda_svc.py`, `dynamodb.py`) into sub-modules by feature area | **Low** — improves maintainability for the largest services | Low |

---

### 5.4 `/mnt/c/Tools/code/ministack-huawei/tests/`

**Predominant Language:** Python 3.10+ (pytest)

**Main Functionality:** Integration test suite. 48 test files, one per AWS service, plus shared configuration (`conftest.py`). Tests use `boto3` clients against the running MiniStack endpoint. Parallel execution via `pytest-xdist` with explicit serial test markers for tests that manipulate global state.

**Key Files:**
- `conftest.py` (277 lines) — Session-scoped fixtures: server reset, boto3 client factory, serial test marking, health check wait.
- `test_*.py` (48 files) — One test file per service, exercising CRUD operations, edge cases, error handling, and cross-service integration.

**Security Concerns:** None significant. Test files intentionally use hardcoded test credentials.

**Improvement Suggestions:**

| # | Suggestion | Impact | Priority |
|---|-----------|--------|----------|
| 1 | Add mutation testing to verify test suite detects actual code changes | **Medium** — increases confidence in test coverage | Medium |
| 2 | Add property-based testing (Hypothesis) for complex parsers (DynamoDB expressions, S3 XML) | **Medium** — catches edge cases | Medium |
| 3 | Add benchmark tests for response latency and throughput | **Low** — tracks performance regressions | Low |

---

### 5.5 `/mnt/c/Tools/code/ministack-huawei/bin/`

**Predominant Language:** Bash

**Main Functionality:** CLI helper script `awslocal` — a thin wrapper around the AWS CLI that automatically sets the `--endpoint-url` to the local MiniStack endpoint and provides default test credentials.

**Security Concerns:**

| # | Vulnerability | Severity | Location | Description | Suggestion |
|---|--------------|----------|----------|-------------|------------|
| 1 | Default credentials in script | **Low** | `bin/awslocal` | Hardcoded `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`. Acceptable for a local dev tool, but credentials could leak in shell history or process listings. | Document that this is for local development only. |

**Improvement Suggestions:**

| # | Suggestion | Impact | Priority |
|---|-----------|--------|----------|
| 1 | Add `--no-sign-request` flag support for anonymous operations | **Low** — convenience feature | Low |

---

### 5.6 `/mnt/c/Tools/code/ministack-huawei/Testcontainers/`

**Predominant Language:** Multi-language (Python, Go, Java)

**Main Functionality:** Testcontainers integration examples and test files for three languages, enabling developers to spin up MiniStack containers programmatically in their test suites.

**Subdirectories:**
- `python-testcontainers/` — Python `test_ministack.py`, `requirements.txt`, `README.md`
- `go-testcontainers/` — Go `ministack_test.go`, `go.mod`, `go.sum`, `README.md`
- `java-testcontainers/` — Java `pom.xml`, `src/` directory, `README.md`

**Security Concerns:** None. These are integration examples.

**Improvement Suggestions:**

| # | Suggestion | Impact | Priority |
|---|-----------|--------|----------|
| 1 | Add version pinning for Testcontainers dependencies | **Medium** — ensures reproducible builds | Medium |
| 2 | Add example with Docker network isolation | **Low** — demonstrates best practices | Low |

---

### 5.7 `/mnt/c/Tools/code/ministack-huawei/.github/`

**Predominant Language:** YAML (GitHub Actions workflows), JSON Schema (issue templates)

**Main Functionality:** CI/CD pipeline configuration and issue templates.

**Key Files:**
- `workflows/ci.yml` — Runs on push/PR: sets up Python 3.12, installs dependencies, starts MiniStack with Redis, runs parallel tests (`pytest-xdist -n 3`), then serial tests.
- `workflows/docker-publish.yml` — Builds and publishes Docker images to `nahuelnucera/ministack` and `ministackorg/ministack`.
- `workflows/pypi-publish.yml` — Builds and publishes Python package to PyPI.
- `ISSUE_TEMPLATE/bug_report.yml` — Bug report template.
- `ISSUE_TEMPLATE/new_service.yml` — New service request template.

**Security Concerns:**

| # | Vulnerability | Severity | Location | Description | Suggestion |
|---|--------------|----------|----------|-------------|------------|
| 1 | PyPI/Docker publish workflows | **Medium** | `.github/workflows/pypi-publish.yml`, `docker-publish.yml` | Ensure these workflows use OIDC-based trusted publishing (PyPI) and Docker Hub token with minimal permissions. Verify branch protection rules prevent unauthorized releases. | Use PyPI trusted publishing (OIDC); restrict Docker push to protected branches only. |

**Improvement Suggestions:**

| # | Suggestion | Impact | Priority |
|---|-----------|--------|----------|
| 1 | Add `pull_request_target` security scanning workflow for dependency vulnerabilities | **High** — catches supply chain risks | High |
| 2 | Add CodeQL static analysis to CI pipeline | **Medium** — automated vulnerability detection | Medium |
| 3 | Add a release workflow that generates changelog and creates GitHub release | **Low** — improves release process | Low |

---

## 6. Overall Security Assessment

### Summary of Vulnerabilities by Severity

| Severity | Count | Key Issues |
|----------|-------|------------|
| **High** | 1 | `eval()` in persistence.py — arbitrary code execution via crafted state files |
| **Medium** | 5 | Wildcard CORS, subprocess execution of user scripts, config endpoint setattr, PyPI/Docker publish permissions, Glue ETL subprocess |
| **Low** | 4 | NUL-byte key separator, hardcoded test credentials, no body size limits, no input length limits |

### General Security Posture: **Good for a local development tool**

The project is designed for local development environments, which inherently reduces the attack surface compared to production-facing services. Key security strengths include:

- Use of `defusedxml` for safe XML parsing (prevents XXE attacks)
- Zip-slip validation in Lambda layer extraction
- Account-scoped state isolation via `AccountScopedDict`
- Non-root Docker container user (`ministack:ministack`)
- Pure Python health check (no external binary dependencies)

The primary actionable item is the `eval()` call in `persistence.py`, which should be replaced immediately.

---

## 7. Architecture Quality Assessment

### Strengths
- **Clean separation of concerns:** Core infrastructure (`core/`) is cleanly separated from service implementations (`services/`)
- **Consistent patterns:** All service modules follow the same `handle_request` / `reset` / `get_state` pattern
- **Multi-tenancy done right:** `AccountScopedDict` provides transparent account isolation without code duplication
- **Comprehensive test coverage:** 48 test files covering all 41 services
- **Minimal dependencies:** Core requires only `uvicorn`, `httptools`, `pyyaml`, `defusedxml`

### Areas for Improvement
- **File size:** Several service files exceed 2,000-3,000 lines, making maintenance challenging
- **Code duplication:** Response formatting and error handling patterns are repeated across many service files
- **Type coverage:** No type hints on most service handler functions
- **Error handling:** Some services return generic 500 errors instead of AWS-specific error codes

### Recommended Priorities
1. **Immediate:** Replace `eval()` with `ast.literal_eval()` in `persistence.py`
2. **High:** Add request body size limits across all service handlers
3. **High:** Add resource limits (memory, timeout) for Lambda workers
4. **Medium:** Extract shared response patterns into base utilities
5. **Medium:** Add type hints to public API functions
6. **Low:** Split large service files into feature sub-modules

---

*Report generated on 2026-04-12 based on MiniStack v1.2.5 source code analysis.*

---

## 8. Huawei Cloud Adaptation (MiniStack-Huawei)

### 8.1 Overview

A variant has been created to emulate **Huawei Cloud** services alongside (or instead of) the AWS services.
The adaptation adds **17 Huawei Cloud services** while reusing the existing AWS service implementations where possible.

### 8.2 New Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `ministack/core/auth_huawei.py` | ~340 | AK/SK HMAC-SHA256 signature verification, IAM token management, credential registry |
| `ministack/services/obs.py` | ~40 | OBS Object Storage (delegates to S3 handler, adds Huawei headers) |
| `ministack/services/iam_hw.py` | ~180 | IAM token authentication (`POST /v3/auth/tokens`), project/user listing |
| `ministack/services/smn.py` | ~200 | Simple Message Notification (topics, publish, subscribe) |
| `ministack/services/functiongraph.py` | ~280 | FunctionGraph serverless (CRUD, invoke via lambda_runtime worker pool, aliases) |
| `ministack/services/rds_hw.py` | ~160 | RDS Huawei (instance CRUD, start/stop/reboot actions) |
| `ministack/services/dcs.py` | ~160 | Distributed Cache Service (Redis/Memcached instance CRUD) |
| `ministack/services/lts.py` | ~210 | Log Tank Service (log groups, streams, event push/query) |
| `ministack/services/vpc_hw.py` | ~250 | VPC Huawei (VPC, subnet, security group CRUD) |
| `ministack/services/huawei_extended.py` | ~200 | Extended services: DMS, AOM, ECS, APIG, DIS, KMS, CSMS, CCE, RFS |
| `ministack/services/{dms,aom,ecs_hw,apig,dis,kms_hw,csms,cce,rfs}.py` | ~2 each | Thin wrapper modules delegating to huawei_extended.py |
| `docker-compose.huawei.yml` | ~45 | Docker Compose for Huawei-only mode |
| `tests/test_huawei_services.py` | ~260 | Integration tests for 8 priority Huawei services |
| `README_HUAWEI.md` | ~200 | Documentation with SDK examples, Terraform config, service matrix |

### 8.3 Modified Files

| File | Changes |
|------|---------|
| `ministack/core/router.py` | Added `HUAWEI_SERVICE_PATTERNS`, `_detect_huawei_service()`, dual-mode routing in `detect_service()` |
| `ministack/app.py` | Added 17 Huawei imports, SERVICE_HANDLERS entries, `/_huawei/health` and `/_huawei/reset` endpoints, `_reset_huawei_state()`, Huawei services in persistence |
| `Dockerfile` | Added `HUAWEI_MODE`, `HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`, `HUAWEICLOUD_PROJECT_ID`, `HUAWEICLOUD_REGION` env vars |

### 8.4 Huawei Service Architecture

```
Request → Router (detect_service)
  ├── HUAWEI_MODE=1: All requests → Huawei services
  ├── HUAWEI_MODE=2: Huawei headers → Huawei services, else → AWS services
  └── HUAWEI_MODE=0: All requests → AWS services (original behavior)

Huawei Service Mapping:
  OBS ← S3 handler (S3-compatible protocol)
  FunctionGraph ← lambda_runtime.py worker pool
  DCS ← ElastiCache patterns
  RDS Huawei ← RDS patterns
  VPC Huawei ← EC2 VPC patterns
  SMN ← SNS patterns
  LTS ← CloudWatch Logs patterns
  Extended services ← Lightweight stubs
```

### 8.5 Huawei-Specific Security Considerations

| # | Concern | Severity | Description | Suggestion |
|---|---------|----------|-------------|------------|
| 1 | Default test credentials | **Medium** | `HUAWEICLOUD_SDK_AK=test`, `SK=test` are hardcoded defaults | Document that these must be changed for shared environments |
| 2 | Token validation not cryptographic | **Low** | IAM tokens are UUIDs stored in memory, not JWT or signed tokens | Acceptable for local emulation; document limitation |
| 3 | Signature verification complexity | **Low** | HMAC-SHA256 implementation follows Huawei v4 algorithm but is simplified | Add unit tests for edge cases in signature verification |

### 8.6 Testing Coverage

The `tests/test_huawei_services.py` file covers:
- **IAM**: Token creation, project listing
- **OBS**: Bucket creation and listing
- **SMN**: Topic CRUD, message publishing
- **FunctionGraph**: Function creation, listing, retrieval
- **RDS**: Instance creation, listing
- **DCS**: Instance creation, listing
- **LTS**: Log group creation, stream creation, log push
- **VPC**: VPC, subnet, and security group creation
- **Admin endpoints**: Health check and reset

Total: ~30 test cases across 8 service classes + admin endpoints.
