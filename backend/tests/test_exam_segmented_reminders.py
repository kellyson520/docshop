from datetime import timedelta

from app.models.exam_schedule import ExamReminder
from app.models.project import Project
from app.utils.time import utc_now


def _create_project(db_session, test_user, name="Segmented Reminder Project"):
    project = Project(name=name, description="for segmented reminders", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _exam_payload(project_id, name="Segmented Exam", start_delta=None, offsets=None):
    start_delta = start_delta or timedelta(days=1)
    start_time = (utc_now() + start_delta).isoformat() + "Z"
    end_time = (utc_now() + start_delta + timedelta(hours=2)).isoformat() + "Z"
    payload = {
        "name": name,
        "description": "custom reminder offsets",
        "start_time": start_time,
        "end_time": end_time,
        "project_id": project_id,
    }
    if offsets is not None:
        payload["reminder_offsets_minutes"] = offsets
    return payload


def test_create_exam_accepts_custom_segmented_reminder_offsets(client, auth_headers, db_session, test_user):
    project = _create_project(db_session, test_user)

    response = client.post(
        "/api/v1/exams",
        headers=auth_headers,
        json=_exam_payload(project.id, offsets=[1440, 120, 30, 10, 0]),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["reminder_offsets_minutes"] == [1440, 120, 30, 10, 0]
    assert data["reminder_15min"] == 0
    assert data["reminder_5min"] == 0
    assert data["reminder_start"] == 1

    reminders = db_session.query(ExamReminder).filter(ExamReminder.exam_id == data["id"]).all()
    assert sorted(r.reminder_type for r in reminders) == [
        "before_10",
        "before_120",
        "before_1440",
        "before_30",
        "start",
    ]


def test_create_exam_without_offsets_exposes_legacy_reminders_as_offsets(client, auth_headers, db_session, test_user):
    project = _create_project(db_session, test_user, "Legacy Reminder Project")
    payload = _exam_payload(project.id, name="Legacy Reminder Exam")
    payload.update({"reminder_15min": 1, "reminder_5min": 1, "reminder_start": 1})

    response = client.post("/api/v1/exams", headers=auth_headers, json=payload)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["reminder_offsets_minutes"] == [15, 5, 0]


def test_upcoming_uses_custom_offset_window_once(client, auth_headers, db_session, test_user):
    project = _create_project(db_session, test_user, "Upcoming Reminder Project")

    create_response = client.post(
        "/api/v1/exams",
        headers=auth_headers,
        json=_exam_payload(
            project.id,
            name="Upcoming Segmented Exam",
            start_delta=timedelta(minutes=25),
            offsets=[30, 10, 0],
        ),
    )
    assert create_response.status_code == 201
    exam_id = create_response.json()["data"]["id"]

    upcoming_response = client.get("/api/v1/exams/upcoming", headers=auth_headers)

    assert upcoming_response.status_code == 200
    items = upcoming_response.json()["data"]["items"]
    reminder_types = [item["reminder_type"] for item in items if item["exam_id"] == exam_id]
    assert reminder_types == ["before_30"]

    second_response = client.get("/api/v1/exams/upcoming", headers=auth_headers)
    second_items = second_response.json()["data"]["items"]
    assert [item for item in second_items if item["exam_id"] == exam_id] == []



def test_create_exam_accepts_flexible_non_preset_reminder_offsets(client, auth_headers, db_session, test_user):
    project = _create_project(db_session, test_user, "Flexible Reminder Project")

    response = client.post(
        "/api/v1/exams",
        headers=auth_headers,
        json=_exam_payload(project.id, name="Flexible Reminder Exam", offsets=[43200, 10007, 123, 0]),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["reminder_offsets_minutes"] == [43200, 10007, 123, 0]

    reminders = db_session.query(ExamReminder).filter(ExamReminder.exam_id == data["id"]).all()
    assert sorted(r.reminder_type for r in reminders) == [
        "before_10007",
        "before_123",
        "before_43200",
        "start",
    ]
