import pytest

pytestmark = pytest.mark.django_db

URL = "/api/curriculum/"


class TestCourseAPI:
    def test_list_courses(self, student_api, course):
        resp = student_api.get(f"{URL}courses/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1
        assert resp.data["results"][0]["code"] == "SBVL"

    def test_retrieve_course(self, student_api, course):
        resp = student_api.get(f"{URL}courses/{course.id}/")
        assert resp.status_code == 200
        assert resp.data["code"] == "SBVL"
        assert resp.data["name"] == "Suc ben vat lieu"


class TestMicroTaskAPI:
    def test_list_tasks(self, student_api, micro_tasks):
        resp = student_api.get(f"{URL}tasks/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1
