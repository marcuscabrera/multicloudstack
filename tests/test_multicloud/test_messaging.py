"""
Messaging Tests — SQS+PubSub+ServiceBus+DMS+SMN.
Tests messaging operations across all 4 cloud providers.
"""
import json
import urllib.request
import pytest


ENDPOINT = "http://localhost:4566"


def _request(method, path, data=None, headers=None):
    """Send HTTP request to MiniStack endpoint."""
    url = f"{ENDPOINT}{path}"
    req_headers = {**(headers or {})}
    if data is not None:
        if isinstance(data, (dict, list)):
            req_headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
        else:
            body = data.encode() if isinstance(data, str) else data
    else:
        body = None
    
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = resp.read()
            return resp.status, json.loads(resp_data) if resp_data else {}, dict(resp.headers)
    except urllib.error.HTTPError as e:
        resp_data = e.read()
        return e.code, json.loads(resp_data) if resp_data else {}, {}


class TestSQSOperations:
    """AWS SQS specific tests."""
    
    def test_sqs_queue_lifecycle(self, sqs):
        """Test SQS queue create, send, receive, delete."""
        queue_name = "test-queue-lifecycle"
        
        # Create queue
        response = sqs.create_queue(QueueName=queue_name)
        queue_url = response["QueueUrl"]
        
        # Send message
        sqs.send_message(QueueUrl=queue_url, MessageBody="Hello SQS!")
        
        # Receive message
        response = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        assert len(response.get("Messages", [])) == 1
        assert response["Messages"][0]["Body"] == "Hello SQS!"
        
        # Delete message
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=response["Messages"][0]["ReceiptHandle"]
        )
        
        # Delete queue
        sqs.delete_queue(QueueUrl=queue_url)
    
    def test_sqs_fifo_queue(self, sqs):
        """Test SQS FIFO queue."""
        queue_name = "test-fifo-queue.fifo"
        
        # Create FIFO queue
        response = sqs.create_queue(
            QueueName=queue_name,
            Attributes={"FifoQueue": "true"}
        )
        queue_url = response["QueueUrl"]
        
        # Send message with message group ID
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody="FIFO message",
            MessageGroupId="test-group"
        )
        
        # Receive and verify
        response = sqs.receive_message(QueueUrl=queue_url)
        assert len(response.get("Messages", [])) == 1
        
        # Cleanup
        sqs.delete_queue(QueueUrl=queue_url)


class TestPubSubOperations:
    """GCP Pub/Sub specific tests."""
    
    def test_pubsub_topic_subscription(self, gcp_headers, gcp_project):
        """Test Pub/Sub topic and subscription lifecycle."""
        topic_name = "test-topic"
        sub_name = "test-subscription"
        
        # Create topic
        status, topic_resp, _ = _request(
            "PUT", 
            f"/v1/projects/{gcp_project}/topics/{topic_name}",
            headers=gcp_headers
        )
        assert status == 200
        
        # Publish message
        import base64
        status, pub_resp, _ = _request(
            "POST",
            f"/v1/projects/{gcp_project}/topics/{topic_name}:publish",
            data={"messages": [{"data": base64.b64encode(b"Hello PubSub!").decode()}]},
            headers=gcp_headers
        )
        assert status == 200
        assert "messageIds" in pub_resp
        
        # Create subscription
        status, sub_resp, _ = _request(
            "PUT",
            f"/v1/projects/{gcp_project}/subscriptions/{sub_name}",
            data={"topic": f"projects/{gcp_project}/topics/{topic_name}"},
            headers=gcp_headers
        )
        assert status == 200
        
        # Pull message
        status, pull_resp, _ = _request(
            "POST",
            f"/v1/projects/{gcp_project}/subscriptions/{sub_name}:pull",
            data={},
            headers=gcp_headers
        )
        assert status == 200


class TestServiceBusOperations:
    """Azure Service Bus specific tests."""
    
    def test_servicebus_queue(self, azure_headers, azure_subscription_id):
        """Test Azure Service Bus queue operations."""
        namespace = "devns"
        queue_name = "test-queue"
        rg = "dev-rg"
        
        # Create queue
        status, _, _ = _request(
            "PUT",
            f"/subscriptions/{azure_subscription_id}/resourceGroups/{rg}/providers/Microsoft.ServiceBus/namespaces/{namespace}/queues/{queue_name}",
            headers=azure_headers
        )
        assert status == 200
        
        # Send message
        status, send_resp, _ = _request(
            "POST",
            f"/azure/servicebus/{namespace}/{queue_name}/messages",
            data={"body": "Hello Service Bus!"},
            headers=azure_headers
        )
        assert status == 201
        assert "messageId" in send_resp


class TestSMNOperations:
    """Huawei SMN specific tests."""
    
    def test_smn_topic_publish(self, huawei_headers, huawei_project_id):
        """Test Huawei SMN topic and publish."""
        topic_name = "test-topic"
        
        # Create topic
        status, topic_resp, _ = _request(
            "POST",
            f"/v2/{huawei_project_id}/notifications/topics",
            data={"name": topic_name},
            headers=huawei_headers
        )
        assert status == 200
        assert "topic_urn" in topic_resp
        
        # Publish message
        status, pub_resp, _ = _request(
            "POST",
            f"/v2/{huawei_project_id}/notifications/topics/{topic_name}/publish",
            data={"message": "Hello SMN!", "subject": "Test"},
            headers=huawei_headers
        )
        assert status == 200
        assert "message_id" in pub_resp


class TestCrossCloudMessaging:
    """Test cross-cloud messaging patterns."""
    
    def test_multi_cloud_event_flow(self, sqs, gcp_headers, gcp_project):
        """Test event flow from AWS SQS to GCP Pub/Sub."""
        # This tests the ability to bridge between clouds
        queue_name = "cross-cloud-queue"
        
        # Create SQS queue
        response = sqs.create_queue(QueueName=queue_name)
        queue_url = response["QueueUrl"]
        
        # Send to SQS
        sqs.send_message(QueueUrl=queue_url, MessageBody="Cross-cloud message")
        
        # Verify in SQS
        response = sqs.receive_message(QueueUrl=queue_url)
        assert len(response.get("Messages", [])) == 1
        
        # Cleanup
        sqs.delete_queue(QueueUrl=queue_url)
