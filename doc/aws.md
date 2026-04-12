# AWS Services

## Overview

MiniStack emulates **41 AWS services** on port `4566`. All services share a single ASGI server, making it lightweight and fast (~300MB image, ~50MB RAM idle).

## Quick Start

```bash
./bin/ministack-start aws

# Verify
curl http://localhost:4566/_ministack/health
```

## Core Services

### S3 (Simple Storage Service)

```bash
# Create bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://my-bucket

# Upload object
aws --endpoint-url=http://localhost:4566 s3 cp file.txt s3://my-bucket/

# List objects
aws --endpoint-url=http://localhost:4566 s3 ls s3://my-bucket/

# Download object
aws --endpoint-url=http://localhost:4566 s3 cp s3://my-bucket/file.txt .
```

**Python (boto3):**

```python
import boto3

s3 = boto3.client("s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

s3.create_bucket(Bucket="my-bucket")
s3.put_object(Bucket="my-bucket", Key="hello.txt", Body=b"Hello AWS!")
obj = s3.get_object(Bucket="my-bucket", Key="hello.txt")
print(obj["Body"].read())  # b'Hello AWS!'
```

### SQS (Simple Queue Service)

```bash
# Create queue
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name my-queue

# Send message
aws --endpoint-url=http://localhost:4566 sqs send-message \
  --queue-url http://localhost:4566/000000000000/my-queue \
  --message-body "Hello SQS"

# Receive message
aws --endpoint-url=http://localhost:4566 sqs receive-message \
  --queue-url http://localhost:4566/000000000000/my-queue
```

**Python:**

```python
sqs = boto3.client("sqs", endpoint_url="http://localhost:4566",
                    aws_access_key_id="test", aws_secret_access_key="test")

q = sqs.create_queue(QueueName="my-queue")
sqs.send_message(QueueUrl=q["QueueUrl"], MessageBody="Hello!")
msgs = sqs.receive_message(QueueUrl=q["QueueUrl"])
print(msgs["Messages"][0]["Body"])
```

### DynamoDB

```bash
# Create table
aws --endpoint-url=http://localhost:4566 dynamodb create-table \
  --table-name Users \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Put item
aws --endpoint-url=http://localhost:4566 dynamodb put-item \
  --table-name Users \
  --item '{"id":{"S":"user1"},"name":{"S":"Alice"}}'

# Get item
aws --endpoint-url=http://localhost:4566 dynamodb get-item \
  --table-name Users \
  --key '{"id":{"S":"user1"}}'
```

### Lambda

```bash
# Create function (zip with index.py)
zip function.zip index.py
aws --endpoint-url=http://localhost:4566 lambda create-function \
  --function-name my-function \
  --runtime python3.9 \
  --handler index.handler \
  --role arn:aws:iam::000000000000:role/role \
  --zip-file fileb://function.zip

# Invoke function
aws --endpoint-url=http://localhost:4566 lambda invoke \
  --function-name my-function output.json

cat output.json
```

**Python:**

```python
import json
import zipfile
import io
import boto3

lam = boto3.client("lambda", endpoint_url="http://localhost:4566",
                   aws_access_key_id="test", aws_secret_access_key="test")

# Create function from memory
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("index.py", "def handler(event, context):\n    return {'statusCode': 200, 'body': 'Hello!'}\n")

lam.create_function(
    FunctionName="my-fn",
    Runtime="python3.9",
    Role="arn:aws:iam::000000000000:role/role",
    Handler="index.handler",
    Code={"ZipFile": buf.getvalue()},
)

resp = lam.invoke(FunctionName="my-fn", Payload=json.dumps({"name": "Test"}))
print(json.loads(resp["Payload"].read()))
```

### RDS (Relational Database Service)

```bash
# Create database instance (spins up real Postgres/MySQL container)
aws --endpoint-url=http://localhost:4566 rds create-db-instance \
  --db-instance-identifier mydb \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password password \
  --allocated-storage 20

# Connect to the real database
psql -h localhost -p 15432 -U admin -d mydb
```

**Python:**

```python
import psycopg2

# Connect to real Postgres container spun up by MiniStack
conn = psycopg2.connect(
    host="localhost", port=15432,
    user="admin", password="password", dbname="mydb"
)
cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())
```

### SNS (Simple Notification Service)

```bash
# Create topic
aws --endpoint-url=http://localhost:4566 sns create-topic --name my-topic

# Subscribe
aws --endpoint-url=http://localhost:4566 sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:000000000000:my-topic \
  --protocol email \
  --notification-endpoint test@example.com

# Publish
aws --endpoint-url=http://localhost:4566 sns publish \
  --topic-arn arn:aws:sns:us-east-1:000000000000:my-topic \
  --message "Hello SNS"
```

### IAM / STS

```bash
# Get caller identity
aws --endpoint-url=http://localhost:4566 sts get-caller-identity

# Create role
aws --endpoint-url=http://localhost:4566 iam create-role \
  --role-name MyRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Create user
aws --endpoint-url=http://localhost:4566 iam create-user --user-name MyUser
```

### CloudFormation

```bash
# Create stack from template
aws --endpoint-url=http://localhost:4566 cloudformation create-stack \
  --stack-name my-stack \
  --template-body '{"Resources":{"MyQueue":{"Type":"AWS::SQS::Queue","Properties":{"QueueName":"my-queue"}}}}'

# Describe stack
aws --endpoint-url=http://localhost:4566 cloudformation describe-stacks --stack-name my-stack
```

## Complete Service List

| Service | Status | Notes |
|---------|--------|-------|
| S3 | ✅ Full | Multipart, versioning, object lock, lifecycle |
| SQS | ✅ Full | FIFO, DLQ, batching |
| SNS | ✅ Full | Lambda fanout, SQS fanout |
| DynamoDB | ✅ Full | Streams, TTL, transactions |
| Lambda | ✅ Full | Python + Node.js, warm workers, layers |
| IAM | ✅ Full | Roles, users, policies, instance profiles |
| STS | ✅ Full | AssumeRole, GetCallerIdentity |
| Secrets Manager | ✅ Full | Versioning, rotation stub |
| CloudWatch Logs | ✅ Full | Log groups, streams, filters |
| CloudWatch Metrics | ✅ Full | Alarms, composite alarms |
| SSM Parameter Store | ✅ Full | SecureString, StringList |
| EventBridge | ✅ Full | Rules, targets, Lambda dispatch |
| Kinesis | ✅ Full | Sharding, enhanced fan-out |
| SES / SES v2 | ✅ Full | Templates, configuration sets |
| ACM | ✅ Full | Certificate requests, import |
| WAF v2 | ✅ Full | WebACL, rules, IP sets |
| Step Functions | ✅ Full | ASL interpreter, TestState API |
| API Gateway v1/v2 | ✅ Full | REST + HTTP APIs |
| ELBv2 / ALB | ✅ Full | Lambda targets, rules |
| KMS | ✅ Full | Encrypt, decrypt, aliases |
| RDS | ✅ Full | Real Postgres/MySQL containers |
| ElastiCache | ✅ Full | Real Redis containers |
| EC2 | ✅ Full | Instances, VPCs, SGs, ENIs |
| ECS | ✅ Full | Real Docker containers |
| ECR | ✅ Full | Image registry |
| EFS | ✅ Full | File systems, mount targets |
| CloudFront | ✅ Full | Distributions, OAC |
| CloudFormation | ✅ Full | 66+ provisioners |
| Route 53 | ✅ Full | Hosted zones, record sets |
| Cognito | ✅ Full | User pools, identity pools, JWKS |
| AppSync | ✅ Full | GraphQL APIs |
| Athena | ✅ Full | Real SQL via DuckDB |
| EMR | ✅ Full | Clusters, steps |
| Glue | ✅ Full | Data catalog, jobs |
| Firehose | ✅ Full | S3 destinations |
| AutoScaling | ✅ Full | ASGs, policies, hooks |
| CodeBuild | ✅ Full | Projects, builds |
| Service Discovery | ✅ Full | Namespaces, services |
| EBS | ✅ Full | Volumes, snapshots |
| Cloud Map | ✅ Full | HTTP/Private DNS namespaces |
| S3 Files | ✅ Full | File systems, access points |
| RDS Data API | ✅ Full | ExecuteStatement |

## Admin Endpoints

```bash
# Health
curl http://localhost:4566/_ministack/health

# Reset all state
curl -X POST http://localhost:4566/_ministack/reset

# Runtime config
curl -X POST http://localhost:4566/_ministack/config \
  -H "Content-Type: application/json" \
  -d '{"MINISTACK_ACCOUNT_ID": "123456789012"}'

# LocalStack compatibility
curl http://localhost:4566/_localstack/health
curl http://localhost:4566/health
```
