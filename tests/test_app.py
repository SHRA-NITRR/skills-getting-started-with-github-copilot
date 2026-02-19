"""
Tests for the Mergington High School Activities API
"""

import pytest
import copy
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Create a deep copy of the activities before test
    initial_activities = copy.deepcopy(activities)
    yield
    # Restore activities after test
    activities.clear()
    activities.update(initial_activities)


class TestGetActivities:
    """Test cases for GET /activities endpoint"""

    def test_get_activities_returns_200(self, client, reset_activities):
        """Test that GET /activities returns status 200"""
        response = client.get("/activities")
        assert response.status_code == 200

    def test_get_activities_returns_dict(self, client, reset_activities):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        assert isinstance(response.json(), dict)

    def test_get_activities_contains_activity_names(self, client, reset_activities):
        """Test that activities response contains expected activity names"""
        response = client.get("/activities")
        activities_data = response.json()
        assert "Basketball Team" in activities_data
        assert "Soccer Club" in activities_data

    def test_get_activities_contains_participant_list(self, client, reset_activities):
        """Test that each activity contains a participants list"""
        response = client.get("/activities")
        activities_data = response.json()
        for activity_name, activity_details in activities_data.items():
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Test cases for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_returns_200(self, client, reset_activities):
        """Test that successful signup returns status 200"""
        response = client.post(
            "/activities/Basketball Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200

    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup adds the participant to the activity"""
        initial_count = len(activities["Basketball Team"]["participants"])
        response = client.post(
            "/activities/Basketball Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert len(activities["Basketball Team"]["participants"]) == initial_count + 1
        assert "newstudent@mergington.edu" in activities["Basketball Team"]["participants"]

    def test_signup_returns_success_message(self, client, reset_activities):
        """Test that signup returns a success message"""
        response = client.post(
            "/activities/Art Studio/signup?email=newstudent@mergington.edu"
        )
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]

    def test_signup_duplicate_returns_400(self, client, reset_activities):
        """Test that signing up twice returns 400 error"""
        email = "alex@mergington.edu"
        # First signup should succeed (already registered)
        response = client.post(f"/activities/Basketball Team/signup?email={email}")
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()

    def test_signup_activity_not_found_returns_404(self, client, reset_activities):
        """Test that signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/NonExistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_multiple_different_students(self, client, reset_activities):
        """Test that multiple different students can sign up for same activity"""
        activity_name = "Science Club"
        initial_count = len(activities[activity_name]["participants"])

        response1 = client.post(
            f"/activities/{activity_name}/signup?email=student1@mergington.edu"
        )
        response2 = client.post(
            f"/activities/{activity_name}/signup?email=student2@mergington.edu"
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert len(activities[activity_name]["participants"]) == initial_count + 2


class TestRemoveParticipant:
    """Test cases for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_participant_returns_200(self, client, reset_activities):
        """Test that removing a participant returns status 200"""
        email = activities["Basketball Team"]["participants"][0]
        response = client.delete(
            f"/activities/Basketball Team/participants/{email}"
        )
        assert response.status_code == 200

    def test_remove_participant_removes_from_list(self, client, reset_activities):
        """Test that remove participant removes them from the participants list"""
        email = activities["Soccer Club"]["participants"][0]
        initial_count = len(activities["Soccer Club"]["participants"])

        response = client.delete(f"/activities/Soccer Club/participants/{email}")
        assert response.status_code == 200
        assert len(activities["Soccer Club"]["participants"]) == initial_count - 1
        assert email not in activities["Soccer Club"]["participants"]

    def test_remove_nonexistent_participant_returns_404(self, client, reset_activities):
        """Test that removing non-existent participant returns 404"""
        response = client.delete(
            "/activities/Basketball Team/participants/nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_remove_from_nonexistent_activity_returns_404(self, client, reset_activities):
        """Test that removing from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Club/participants/student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_remove_participant_returns_message(self, client, reset_activities):
        """Test that remove participant returns a success message"""
        email = activities["Drama Club"]["participants"][0]
        response = client.delete(f"/activities/Drama Club/participants/{email}")
        data = response.json()
        assert "message" in data
        assert "Removed" in data["message"]


class TestWorkflow:
    """Test cases for complete workflows"""

    def test_signup_and_remove_workflow(self, client, reset_activities):
        """Test full workflow of signing up and then removing a participant"""
        activity = "Debate Team"
        email = "testworkflow@mergington.edu"

        # Signup
        response1 = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response1.status_code == 200
        assert email in activities[activity]["participants"]

        # Remove
        response2 = client.delete(f"/activities/{activity}/participants/{email}")
        assert response2.status_code == 200
        assert email not in activities[activity]["participants"]

    def test_cannot_signup_after_signup_then_remove_and_signup_again(self, client, reset_activities):
        """Test that can signup again after being removed"""
        activity = "Chess Club"
        email = "testagain@mergington.edu"

        # First signup
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200

        # Remove
        response2 = client.delete(f"/activities/{activity}/participants/{email}")
        assert response2.status_code == 200

        # Signup again (should work)
        response3 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response3.status_code == 200
        assert response1.json()["message"] == response3.json()["message"]
