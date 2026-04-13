"""
Serverless Tests — Lambda+Functions+CloudRun+FunctionGraph.
Tests serverless operations across all 4 cloud providers.
"""
import json
import urllib.request
import base64
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


class TestLambdaOperations:
    """AWS Lambda specific tests."""
    
    def test_lambda_function_lifecycle(self, lambda_client):
        """Test Lambda function create, invoke, delete."""
        import zipfile
        import io
        
        function_name = "test-function-lifecycle"
        
        # Create minimal Python function
        code = """
def handler(event, context):
    return {"statusCode": 200, "body": event.get("message", "hello")}
""".strip()
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.py", code)
        zip_buffer.seek(0)
        
        # Create function
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.12",
            Role="arn:aws:iam::000000000000:role/test-role",
            Handler="index.handler",
            Code={"ZipFile": zip_buffer.read()}
        )
        
        # Invoke function
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps({"message": "test-payload"})
        )
        result = json.loads(response["Payload"].read())
        assert result["statusCode"] == 200
        
        # Delete function
        lambda_client.delete_function(FunctionName=function_name)
    
    def test_lambda_nodejs_function(self, lambda_client):
        """Test Node.js Lambda function."""
        import zipfile
        import io
        
        function_name = "test-nodejs-function"
        
        code = """
exports.handler = async (event) => {
    return {statusCode: 200, body: JSON.stringify({received: event.body})};
};
""".strip()
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.js", code)
        zip_buffer.seek(0)
        
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="nodejs18.x",
            Role="arn:aws:iam::000000000000:role/test-role",
            Handler="index.handler",
            Code={"ZipFile": zip_buffer.read()}
        )
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps({"body": "nodejs-test"})
        )
        result = json.loads(response["Payload"].read())
        assert result["statusCode"] == 200
        
        lambda_client.delete_function(FunctionName=function_name)


class TestGCPFunctions:
    """GCP Cloud Functions specific tests."""
    
    def test_gcp_function_deploy_invoke(self, gcp_headers, gcp_project):
        """Test GCP Cloud Function deploy and invoke."""
        function_name = "test-gcp-fn"
        region = "us-central1"
        
        # Deploy function
        status, deploy_resp, _ = _request(
            "POST",
            f"/v1/projects/{gcp_project}/locations/{region}/functions/{function_name}",
            data={
                "entryPoint": "handler",
                "runtime": "python311",
                "sourceUploadUrl": "gs://test-bucket/source.zip"
            },
            headers=gcp_headers
        )
        assert status == 200
        
        # Invoke function
        status, invoke_resp, _ = _request(
            "POST",
            f"/gcp/fn/{function_name}",
            data={"name": "GCP"},
            headers=gcp_headers
        )
        assert status == 200


class TestAzureFunctions:
    """Azure Functions specific tests."""
    
    def test_azure_function_create_invoke(self, azure_headers, azure_subscription_id):
        """Test Azure Function create and invoke."""
        function_app = "myfuncapp"
        function_name = "hello"
        rg = "dev-rg"
        
        # Create function
        status, create_resp, _ = _request(
            "POST",
            f"/subscriptions/{azure_subscription_id}/resourceGroups/{rg}/providers/Microsoft.Web/sites/{function_app}/functions/{function_name}",
            data={
                "name": function_name,
                "code": {"zip": ""}
            },
            headers=azure_headers
        )
        assert status == 200
        
        # Invoke function
        status, invoke_resp, _ = _request(
            "POST",
            "/api/hello",
            data={"name": "Azure"},
            headers=azure_headers
        )
        assert status == 200


class TestFunctionGraph:
    """Huawei FunctionGraph specific tests."""
    
    def test_functiongraph_create_invoke(self, huawei_headers, huawei_project_id):
        """Test Huawei FunctionGraph create and invoke."""
        function_name = "test-huawei-fn"
        
        # Create function
        status, create_resp, _ = _request(
            "POST",
            f"/v2/{huawei_project_id}/fgs/functions",
            data={
                "func_name": function_name,
                "runtime": "Python3.9",
                "handler": "index.handler",
                "memory_size": 256,
                "timeout": 30
            },
            headers=huawei_headers
        )
        assert status == 200
        assert create_resp.get("func_name") == function_name
        
        # List functions
        status, list_resp, _ = _request(
            "GET",
            f"/v2/{huawei_project_id}/fgs/functions",
            headers=huawei_headers
        )
        assert status == 200
        assert "functions" in list_resp


class TestCrossCloudServerless:
    """Test cross-cloud serverless patterns."""
    
    def test_multi_cloud_function_echo(self, lambda_client, gcp_headers, gcp_project):
        """Test Python function echo across AWS and GCP."""
        import zipfile
        import io
        
        # Common handler code
        code = """
def handler(event, context):
    return {"statusCode": 200, "body": event.get("message", "hello")}
""".strip()
        
        # Test AWS Lambda
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.py", code)
        zip_buffer.seek(0)
        
        aws_fn = "cross-cloud-echo-aws"
        lambda_client.create_function(
            FunctionName=aws_fn,
            Runtime="python3.12",
            Role="arn:aws:iam::000000000000:role/test-role",
            Handler="index.handler",
            Code={"ZipFile": zip_buffer.read()}
        )
        
        response = lambda_client.invoke(
            FunctionName=aws_fn,
            Payload=json.dumps({"message": "multi-cloud-test"})
        )
        result = json.loads(response["Payload"].read())
        assert result["statusCode"] == 200
        
        lambda_client.delete_function(FunctionName=aws_fn)
