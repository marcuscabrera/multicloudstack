"""
Database Tests — RDS+CloudSQL+AzureSQL+RDSHuawei.
Tests database operations across all 4 cloud providers.
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


class TestRDSOperations:
    """AWS RDS specific tests."""
    
    def test_rds_instance_lifecycle(self, rds):
        """Test RDS instance create, describe, delete."""
        db_identifier = "test-db-instance"
        
        # Create DB instance
        response = rds.create_db_instance(
            DBInstanceIdentifier=db_identifier,
            DBInstanceClass="db.t2.micro",
            Engine="postgres",
            MasterUsername="admin",
            MasterUserPassword="password123",
            AllocatedStorage=20
        )
        assert response["DBInstance"]["DBInstanceIdentifier"] == db_identifier
        
        # Describe DB instance
        response = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)
        assert len(response["DBInstances"]) == 1
        
        # Delete DB instance
        rds.delete_db_instance(DBInstanceIdentifier=db_identifier, SkipFinalSnapshot=True)


class TestCloudSQLOperations:
    """GCP Cloud SQL specific tests."""
    
    def test_cloudsql_instance_create(self, gcp_headers, gcp_project):
        """Test GCP Cloud SQL instance creation."""
        instance_name = "test-sql-instance"
        
        status, resp, _ = _request(
            "POST",
            f"/sql/v1beta4/projects/{gcp_project}/instances",
            data={
                "name": instance_name,
                "databaseVersion": "POSTGRES_14",
                "settings": {
                    "tier": "db-f1-micro",
                    "backupConfiguration": {"enabled": True}
                }
            },
            headers=gcp_headers
        )
        assert status == 200
        assert resp.get("state") == "RUNNABLE"


class TestAzureSQLOperations:
    """Azure SQL specific tests."""
    
    def test_azure_sql_server_create(self, azure_headers, azure_subscription_id):
        """Test Azure SQL server creation."""
        server_name = "testsqlserver"
        rg = "dev-rg"
        
        status, resp, _ = _request(
            "PUT",
            f"/subscriptions/{azure_subscription_id}/resourceGroups/{rg}/providers/Microsoft.Sql/servers/{server_name}",
            data={
                "name": server_name,
                "properties": {
                    "administratorLogin": "azureadmin",
                    "version": "14"
                }
            },
            headers=azure_headers
        )
        assert status == 200
        assert "fullyQualifiedDomainName" in resp.get("properties", {})


class TestRDSHuaweiOperations:
    """Huawei RDS specific tests."""
    
    def test_rds_huawei_instance_create(self, huawei_headers, huawei_project_id):
        """Test Huawei RDS instance creation."""
        instance_name = "test-rds-huawei"
        
        status, resp, _ = _request(
            "POST",
            f"/v3/{huawei_project_id}/instances",
            data={
                "name": instance_name,
                "datastore": {"type": "MySQL", "version": "8.0"},
                "flavor_ref": "rds.mysql.c2.large.2",
                "volume": {"size": 40, "type": "ULTRAHIGH"},
                "vpc_id": "test-vpc",
                "subnet_id": "test-subnet",
                "security_group_id": "test-sg"
            },
            headers=huawei_headers
        )
        assert status == 202
        assert "instance" in resp
