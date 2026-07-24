import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_dynamodb(mocker):
    # Mock users_table
    mock_users = MagicMock()
    # Mock chat table
    mock_table = MagicMock()
    
    mocker.patch.object(main, 'users_table', mock_users)
    mocker.patch.object(main, 'table', mock_table)
    
    return {'users': mock_users, 'chat': mock_table}

def test_register_success(mock_dynamodb):
    # Setup mock to return no item (user doesn't exist)
    mock_dynamodb['users'].get_item.return_value = {}
    
    response = client.post("/api/register", json={
        "username": "testuser",
        "password": "testpassword123"
    })
    
    assert response.status_code == 200
    assert response.json() == {"success": True}
    mock_dynamodb['users'].put_item.assert_called_once()

def test_register_duplicate(mock_dynamodb):
    # Setup mock to return an item (user exists)
    mock_dynamodb['users'].get_item.return_value = {"Item": {"username": "testuser"}}
    
    response = client.post("/api/register", json={
        "username": "testuser",
        "password": "testpassword123"
    })
    
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]

def test_login_success(mock_dynamodb):
    # We need to hash a password to put in the mock DB
    hashed = main.pwd_context.hash("testpassword123")
    mock_dynamodb['users'].get_item.return_value = {
        "Item": {
            "username": "testuser",
            "password_hash": hashed
        }
    }
    
    response = client.post("/api/login", json={
        "username": "testuser",
        "password": "testpassword123"
    })
    
    assert response.status_code == 200
    assert response.json() == {"success": True}

def test_login_invalid_password(mock_dynamodb):
    hashed = main.pwd_context.hash("testpassword123")
    mock_dynamodb['users'].get_item.return_value = {
        "Item": {
            "username": "testuser",
            "password_hash": hashed
        }
    }
    
    response = client.post("/api/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    
def test_get_profile_success(mock_dynamodb):
    mock_dynamodb['users'].get_item.return_value = {
        "Item": {
            "username": "testuser",
            "created_at": "2026-07-24T12:00:00Z"
        }
    }
    
    response = client.get("/api/profile/testuser")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["profile"]["username"] == "testuser"
    assert data["profile"]["created_at"] == "2026-07-24T12:00:00Z"

def test_get_history_success(mock_dynamodb):
    mock_dynamodb['chat'].query.return_value = {
        "Items": [
            {
                "username": "testuser",
                "timestamp": "2026-07-24T12:01:00Z",
                "user_message": "Hello",
                "ai_response": "Hi there",
                "feature_type": "career_advice"
            }
        ]
    }
    
    response = client.get("/api/history/testuser")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["history"]) == 1
    assert data["history"][0]["user_message"] == "Hello"

def test_chat_endpoint(mock_dynamodb, mocker):
    # Mock the Groq client
    mock_client = MagicMock()
    # Deep mock for client.chat.completions.create(...).choices[0].message.content
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a mocked AI response."
    mock_client.chat.completions.create.return_value = mock_response
    
    mocker.patch.object(main, 'client', mock_client)
    
    response = client.post("/api/chat", json={
        "message": "What should I do with my life?",
        "feature_type": "career_advice",
        "username": "testuser"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["response"] == "This is a mocked AI response."
    
    # Ensure it was saved to history
    mock_dynamodb['chat'].put_item.assert_called_once()
