"""
Unified Storage Tests — S3/GCS/Blob/OBS CRUD end-to-end.
Tests storage operations across all 4 cloud providers.
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
        elif isinstance(data, bytes):
            body = data
            req_headers["Content-Type"] = "application/octet-stream"
        else:
            body = str(data).encode()
    else:
        body = None
    
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = resp.read()
            return resp.status, resp_data, dict(resp.headers)
    except urllib.error.HTTPError as e:
        resp_data = e.read()
        return e.code, resp_data, {}


class TestUnifiedStorage:
    """Test unified storage operations across all 4 clouds."""
    
    @pytest.mark.parametrize("provider,bucket_endpoint,object_path,headers", [
        ("aws", "/my-bucket-aws", "/hello.txt", 
         {"Authorization": "AWS4-HMAC-SHA256 Credential=test"}),
        ("gcp", "/storage/v1/b/my-bucket-gcp", "/o/hello.txt", 
         {"Authorization": "Bearer ya29.test"}),
        ("azure", f"/azure/blob/devstoreaccount1/my-container-azure", "/hello.txt", 
         {"x-ms-date": "2026-04-12T23:00:00Z"}),
        ("huawei", "/v1/my-obs-bucket", "/hello.txt", 
         {"X-Sdk-Date": "20260412T230000Z"}),
    ])
    async def test_create_read_delete_object(self, provider, bucket_endpoint, object_path, headers):
        """Teste unificado: PUT → GET → DELETE em todos os 4 clouds."""
        
        # 1. CREATE bucket/container
        if provider == "aws":
            status, _, _ = _request("PUT", bucket_endpoint, headers=headers)
            assert status in (200, 201, 409)  # 409 = already exists
        elif provider == "gcp":
            status, _, _ = _request("POST", "/storage/v1/b", 
                                   data={"name": "my-bucket-gcp"}, headers=headers)
            assert status in (200, 409)
        elif provider == "azure":
            status, _, _ = _request("PUT", f"{bucket_endpoint}?restype=container", headers=headers)
            assert status in (200, 201, 204, 409)
        elif provider == "huawei":
            status, _, _ = _request("PUT", bucket_endpoint, headers=headers)
            assert status in (200, 204, 409)
        
        # 2. PUT object
        content = b"Hello Multi-Cloud!"
        if provider == "aws":
            status, _, _ = _request(
                "PUT", f"{bucket_endpoint}{object_path}", 
                data=content, 
                headers={**headers, "Content-Type": "text/plain"}
            )
            assert status == 200
        elif provider == "gcp":
            status, _, _ = _request(
                "POST", f"{bucket_endpoint}",
                data={"name": "hello.txt", "content": content.decode()},
                headers=headers
            )
            assert status == 200
        elif provider == "azure":
            status, _, _ = _request(
                "PUT", f"{bucket_endpoint}{object_path}",
                data=content,
                headers={**headers, "Content-Type": "text/plain"}
            )
            assert status in (200, 201)
        elif provider == "huawei":
            status, _, _ = _request(
                "PUT", f"{bucket_endpoint}{object_path}",
                data=content,
                headers={**headers, "Content-Type": "text/plain"}
            )
            assert status == 200
        
        # 3. GET object  
        if provider == "aws":
            status, resp_data, _ = _request("GET", f"{bucket_endpoint}{object_path}", headers=headers)
            assert status == 200
            assert b"Hello Multi-Cloud!" in resp_data
        elif provider == "gcp":
            status, resp_data, _ = _request("GET", f"{bucket_endpoint}?alt=media", headers=headers)
            assert status == 200
            assert b"Hello Multi-Cloud!" in resp_data
        elif provider == "azure":
            status, resp_data, _ = _request("GET", f"{bucket_endpoint}{object_path}", headers=headers)
            assert status == 200
            assert b"Hello Multi-Cloud!" in resp_data
        elif provider == "huawei":
            status, resp_data, _ = _request("GET", f"{bucket_endpoint}{object_path}", headers=headers)
            assert status == 200
            assert b"Hello Multi-Cloud!" in resp_data
        
        # 4. DELETE object
        if provider == "aws":
            status, _, _ = _request("DELETE", f"{bucket_endpoint}{object_path}", headers=headers)
            assert status == 204
        elif provider == "gcp":
            status, _, _ = _request("DELETE", f"/storage/v1/b/my-bucket-gcp/o/hello.txt", headers=headers)
            assert status == 204
        elif provider == "azure":
            status, _, _ = _request("DELETE", f"{bucket_endpoint}{object_path}", headers=headers)
            assert status in (200, 202, 204)
        elif provider == "huawei":
            status, _, _ = _request("DELETE", f"{bucket_endpoint}{object_path}", headers=headers)
            assert status == 204


class TestS3Operations:
    """AWS S3 specific tests."""
    
    def test_s3_bucket_lifecycle(self, s3_client):
        """Test S3 bucket create, list, delete lifecycle."""
        import botocore.exceptions
        
        bucket_name = "test-bucket-lifecycle"
        
        # Create
        s3_client.create_bucket(Bucket=bucket_name)
        
        # List and verify
        response = s3_client.list_buckets()
        bucket_names = [b["Name"] for b in response["Buckets"]]
        assert bucket_name in bucket_names
        
        # Delete
        s3_client.delete_bucket(Bucket=bucket_name)
        
        # Verify deletion
        response = s3_client.list_buckets()
        bucket_names = [b["Name"] for b in response["Buckets"]]
        assert bucket_name not in bucket_names
    
    def test_s3_object_versioning(self, s3_client):
        """Test S3 object versioning."""
        bucket_name = "test-versioning-bucket"
        key = "versioned-object.txt"
        
        # Create bucket with versioning
        s3_client.create_bucket(Bucket=bucket_name)
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Enabled"}
        )
        
        # Put object twice
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"version1")
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"version2")
        
        # List versions
        response = s3_client.list_object_versions(Bucket=bucket_name)
        assert len(response.get("Versions", [])) >= 2
        
        # Cleanup
        s3_client.delete_bucket(Bucket=bucket_name)


class TestGCSOperations:
    """GCP Cloud Storage specific tests."""
    
    def test_gcs_bucket_iam(self, gcp_headers, gcp_project):
        """Test GCS bucket IAM policy."""
        bucket_name = "test-iam-bucket"
        
        # Create bucket
        status, _, _ = _request("POST", "/storage/v1/b", data={"name": bucket_name}, headers=gcp_headers)
        assert status == 200
        
        # Get IAM policy
        status, policy, _ = _request(
            "GET", 
            f"/storage/v1/b/{bucket_name}/iam/test",
            headers=gcp_headers
        )
        assert status == 200
        
        # Set IAM policy
        new_policy = {
            "bindings": [
                {"role": "roles/storage.objectViewer", "members": ["user:test@example.com"]}
            ]
        }
        status, _, _ = _request(
            "POST",
            f"/storage/v1/b/{bucket_name}/iam/test",
            data=new_policy,
            headers=gcp_headers
        )
        assert status == 200


class TestAzureBlobOperations:
    """Azure Blob Storage specific tests."""
    
    def test_blob_container_metadata(self, azure_headers):
        """Test Azure blob container metadata."""
        container_name = "test-metadata-container"
        
        # Create container
        status, _, _ = _request(
            "PUT", 
            f"/azure/blob/devstoreaccount1/{container_name}?restype=container",
            headers=azure_headers
        )
        assert status in (200, 201, 204)
        
        # Set metadata
        status, _, _ = _request(
            "PUT",
            f"/azure/blob/devstoreaccount1/{container_name}?restype=container&comp=metadata",
            headers={**azure_headers, "x-ms-meta-custom": "value"}
        )
        assert status in (200, 204)


class TestOBSSOperations:
    """Huawei OBS specific tests."""
    
    def test_obs_bucket_location(self, huawei_headers):
        """Test OBS bucket location constraint."""
        bucket_name = "test-location-bucket"
        
        # Create bucket
        status, _, _ = _request("PUT", f"/v1/{bucket_name}", headers=huawei_headers)
        assert status in (200, 204)
        
        # Get location
        status, location, _ = _request("GET", f"/v1/{bucket_name}?location", headers=huawei_headers)
        assert status == 200
