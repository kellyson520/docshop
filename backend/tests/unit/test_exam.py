"""
考试提醒模块单元测试

测试考试相关的API功能，包括考试的增删改查、提醒管理等。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.models.exam_schedule import ExamSchedule, ExamReminder, ExamStatus
from app.models.project import Project
from app.schemas.exam import (
    ExamCreate, ExamUpdate, ExamResponse, ExamListItem,
    ExamListResponse, UpcomingExamItem, ExamDismissRequest
)
from app.exceptions import ResourceNotFound, ValidationError, PermissionDenied, DatabaseError


# ===== Fixtures =====

@pytest.fixture
def mock_exam():
    """创建模拟考试"""
    exam = Mock()
    exam.id = "test-exam-id-123"
    exam.name = "测试考试"
    exam.description = "这是一个测试考试"
    exam.start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    exam.end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
    exam.project_id = "test-project-id-123"
    exam.status = ExamStatus.upcoming.value
    exam.reminder_15min = 1
    exam.reminder_5min = 1
    exam.reminder_start = 1
    exam.created_by = "test-user-id-123"
    exam.created_at = datetime.utcnow().isoformat() + "Z"
    exam.updated_at = datetime.utcnow().isoformat() + "Z"
    return exam


@pytest.fixture
def mock_ongoing_exam():
    """创建模拟进行中考试"""
    exam = Mock()
    exam.id = "ongoing-exam-id-456"
    exam.name = "进行中考试"
    exam.description = "这是一个进行中的考试"
    exam.start_time = (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z"
    exam.end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
    exam.project_id = "test-project-id-123"
    exam.status = ExamStatus.ongoing.value
    exam.reminder_15min = 1
    exam.reminder_5min = 1
    exam.reminder_start = 1
    exam.created_by = "test-user-id-123"
    exam.created_at = datetime.utcnow().isoformat() + "Z"
    exam.updated_at = datetime.utcnow().isoformat() + "Z"
    return exam


@pytest.fixture
def mock_expired_exam():
    """创建模拟已过期考试"""
    exam = Mock()
    exam.id = "expired-exam-id-789"
    exam.name = "已过期考试"
    exam.description = "这是一个已过期的考试"
    exam.start_time = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    exam.end_time = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
    exam.project_id = "test-project-id-123"
    exam.status = ExamStatus.expired.value
    exam.reminder_15min = 1
    exam.reminder_5min = 1
    exam.reminder_start = 1
    exam.created_by = "test-user-id-123"
    exam.created_at = datetime.utcnow().isoformat() + "Z"
    exam.updated_at = datetime.utcnow().isoformat() + "Z"
    return exam


@pytest.fixture
def exam_create_data(test_project):
    """考试创建数据"""
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
    return {
        "name": "新考试",
        "description": "考试描述",
        "start_time": start_time,
        "end_time": end_time,
        "project_id": test_project.id,
        "reminder_15min": 1,
        "reminder_5min": 1,
        "reminder_start": 1
    }


@pytest.fixture
def exam_update_data():
    """考试更新数据"""
    return {
        "name": "更新的考试名称",
        "description": "更新的考试描述",
        "reminder_15min": 0
    }


# ===== 考试列表测试 =====

class TestListExams:
    """测试获取考试列表功能"""

    def test_list_exams_success(self, client, auth_headers, test_user, test_project, db_session):
        """测试成功获取考试列表"""
        # 创建一些测试考试
        for i in range(3):
            start_time = (datetime.utcnow() + timedelta(days=i+1)).isoformat() + "Z"
            end_time = (datetime.utcnow() + timedelta(days=i+1, hours=2)).isoformat() + "Z"
            exam = ExamSchedule(
                name=f"考试{i+1}",
                description=f"描述{i+1}",
                start_time=start_time,
                end_time=end_time,
                project_id=test_project.id,
                status=ExamStatus.upcoming.value,
                created_by=test_user.id
            )
            db_session.add(exam)
        db_session.commit()
        
        response = client.get("/api/v1/exams", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "data" in data
        assert data["data"]["total"] >= 3
        assert len(data["data"]["items"]) >= 3

    def test_list_exams_with_pagination(self, client, auth_headers, test_user, test_project, db_session):
        """测试考试列表分页"""
        # 创建多个考试
        for i in range(10):
            start_time = (datetime.utcnow() + timedelta(days=i+1)).isoformat() + "Z"
            end_time = (datetime.utcnow() + timedelta(days=i+1, hours=2)).isoformat() + "Z"
            exam = ExamSchedule(
                name=f"分页考试{i+1}",
                start_time=start_time,
                end_time=end_time,
                project_id=test_project.id,
                status=ExamStatus.upcoming.value,
                created_by=test_user.id
            )
            db_session.add(exam)
        db_session.commit()
        
        response = client.get("/api/v1/exams?page=1&page_size=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 5
        assert len(data["data"]["items"]) == 5

    def test_list_exams_with_status_filter(self, client, auth_headers, test_user, test_project, db_session):
        """测试考试列表状态过滤"""
        # 创建不同状态的考试
        now = datetime.utcnow()
        
        # upcoming
        exam_upcoming = ExamSchedule(
            name="即将开始考试",
            start_time=(now + timedelta(days=1)).isoformat() + "Z",
            end_time=(now + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        
        # expired
        exam_expired = ExamSchedule(
            name="已结束考试",
            start_time=(now - timedelta(days=2)).isoformat() + "Z",
            end_time=(now - timedelta(days=1)).isoformat() + "Z",
            project_id=test_project.id,
            status=ExamStatus.expired.value,
            created_by=test_user.id
        )
        
        db_session.add_all([exam_upcoming, exam_expired])
        db_session.commit()
        
        # 测试 upcoming 过滤
        response = client.get("/api/v1/exams?status=upcoming", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        for item in items:
            assert item["status"] == "upcoming"

    def test_list_exams_with_project_filter(self, client, auth_headers, test_user, test_project, db_session):
        """测试考试列表项目过滤"""
        # 创建另一个项目
        other_project = Project(
            name="其他项目",
            owner_id=test_user.id,
            share_token="other_token"
        )
        db_session.add(other_project)
        db_session.commit()
        
        # 在两个项目中创建考试
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam1 = ExamSchedule(
            name="项目1考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        exam2 = ExamSchedule(
            name="项目2考试",
            start_time=start_time,
            end_time=end_time,
            project_id=other_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add_all([exam1, exam2])
        db_session.commit()
        
        # 按项目过滤
        response = client.get(f"/api/v1/exams?project_id={test_project.id}", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        for item in items:
            assert item["project_id"] == test_project.id

    def test_list_exams_with_keyword_search(self, client, auth_headers, test_user, test_project, db_session):
        """测试考试列表关键词搜索"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam1 = ExamSchedule(
            name="数学期末考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        exam2 = ExamSchedule(
            name="英语期中考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add_all([exam1, exam2])
        db_session.commit()
        
        response = client.get("/api/v1/exams?keyword=数学", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        for item in items:
            assert "数学" in item["name"]

    def test_list_exams_with_sorting(self, client, auth_headers, test_user, test_project, db_session):
        """测试考试列表排序"""
        for i in range(3):
            start_time = (datetime.utcnow() + timedelta(days=i+1)).isoformat() + "Z"
            end_time = (datetime.utcnow() + timedelta(days=i+1, hours=2)).isoformat() + "Z"
            exam = ExamSchedule(
                name=f"排序考试{i+1}",
                start_time=start_time,
                end_time=end_time,
                project_id=test_project.id,
                status=ExamStatus.upcoming.value,
                created_by=test_user.id
            )
            db_session.add(exam)
        db_session.commit()
        
        response = client.get("/api/v1/exams?sort_by=start_time&sort_order=asc", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        # 验证按开始时间升序排列
        times = [item["start_time"] for item in items]
        assert times == sorted(times)

    def test_list_exams_without_auth(self, client):
        """测试未认证获取考试列表"""
        response = client.get("/api/v1/exams")
        assert response.status_code == 403


# ===== 考试创建测试 =====

class TestCreateExam:
    """测试创建考试功能"""

    def test_create_exam_success(self, client, auth_headers, test_user, test_project, db_session):
        """测试成功创建考试（管理员）"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "新考试",
            "description": "考试描述",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id,
            "reminder_15min": 1,
            "reminder_5min": 1,
            "reminder_start": 1
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "新考试"
        assert data["data"]["description"] == "考试描述"
        assert data["data"]["project_id"] == test_project.id
        assert data["data"]["status"] == "upcoming"

    def test_create_exam_non_admin_forbidden(self, client, viewer_headers, test_project):
        """测试非管理员创建考试被拒绝"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "新考试",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=viewer_headers)
        
        assert response.status_code == 403

    def test_create_exam_project_not_found(self, client, auth_headers):
        """测试为不存在的项目创建考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "新考试",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": "non-existent-id"
        }, headers=auth_headers)
        
        assert response.status_code == 404

    def test_create_exam_with_duplicate_name(self, client, auth_headers, test_user, test_project, db_session):
        """测试在同一项目中创建同名考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        # 先创建一个考试
        exam = ExamSchedule(
            name="重复名称考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 尝试创建同名考试
        response = client.post("/api/v1/exams", json={
            "name": "重复名称考试",
            "start_time": (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z",
            "end_time": (datetime.utcnow() + timedelta(days=2, hours=2)).isoformat() + "Z",
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 400
        assert "同名考试" in response.json()["message"]

    def test_create_exam_with_invalid_time_format(self, client, auth_headers, test_project):
        """测试创建考试时间格式无效"""
        response = client.post("/api/v1/exams", json={
            "name": "时间格式错误考试",
            "start_time": "invalid-time",
            "end_time": "invalid-time",
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_exam_end_time_before_start(self, client, auth_headers, test_project):
        """测试创建考试结束时间早于开始时间"""
        start_time = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "时间错误考试",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_exam_with_empty_name(self, client, auth_headers, test_project):
        """测试创建考试名称为空"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_exam_without_auth(self, client, test_project):
        """测试未认证创建考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "测试考试",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        })
        
        assert response.status_code == 403


# ===== 考试详情测试 =====

class TestGetExam:
    """测试获取考试详情功能"""

    def test_get_exam_success(self, client, auth_headers, test_user, test_project, db_session):
        """测试成功获取考试详情"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="详情考试",
            description="考试详情描述",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.get(f"/api/v1/exams/{exam.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["id"] == exam.id
        assert data["data"]["name"] == "详情考试"
        assert data["data"]["description"] == "考试详情描述"
        assert "time_until_start" in data["data"]
        assert "is_upcoming" in data["data"]

    def test_get_exam_not_found(self, client, auth_headers):
        """测试获取不存在的考试"""
        response = client.get("/api/v1/exams/non-existent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_get_exam_without_auth(self, client, test_user, test_project, db_session):
        """测试未认证获取考试详情"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.get(f"/api/v1/exams/{exam.id}")
        assert response.status_code == 403


# ===== 考试更新测试 =====

class TestUpdateExam:
    """测试更新考试功能"""

    def test_update_exam_success(self, client, auth_headers, test_user, test_project, db_session):
        """测试成功更新考试（管理员）"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="原考试名称",
            description="原描述",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            reminder_15min=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.put(f"/api/v1/exams/{exam.id}", json={
            "name": "新考试名称",
            "description": "新描述",
            "reminder_15min": 0
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "新考试名称"
        assert data["data"]["description"] == "新描述"
        assert data["data"]["reminder_15min"] == 0

    def test_update_exam_non_admin_forbidden(self, client, viewer_headers, test_user, test_project, db_session):
        """测试非管理员更新考试被拒绝"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.put(f"/api/v1/exams/{exam.id}", json={
            "name": "试图修改"
        }, headers=viewer_headers)
        
        assert response.status_code == 403

    def test_update_exam_not_found(self, client, auth_headers):
        """测试更新不存在的考试"""
        response = client.put("/api/v1/exams/non-existent-id", json={
            "name": "新名称"
        }, headers=auth_headers)
        
        assert response.status_code == 404

    def test_update_exam_partial(self, client, auth_headers, test_user, test_project, db_session):
        """测试部分更新考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="原名称",
            description="原描述",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            reminder_15min=1,
            reminder_5min=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 只更新名称
        response = client.put(f"/api/v1/exams/{exam.id}", json={
            "name": "仅更新名称"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "仅更新名称"
        assert data["data"]["description"] == "原描述"
        assert data["data"]["reminder_15min"] == 1

    def test_update_exam_with_duplicate_name(self, client, auth_headers, test_user, test_project, db_session):
        """测试更新为已存在的考试名称"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        # 创建两个考试
        exam1 = ExamSchedule(
            name="考试A",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        exam2 = ExamSchedule(
            name="考试B",
            start_time=(datetime.utcnow() + timedelta(days=2)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=2, hours=2)).isoformat() + "Z",
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add_all([exam1, exam2])
        db_session.commit()
        
        # 尝试将exam2改名为exam1的名称
        response = client.put(f"/api/v1/exams/{exam2.id}", json={
            "name": "考试A"
        }, headers=auth_headers)
        
        assert response.status_code == 400
        assert "同名考试" in response.json()["message"]

    def test_update_exam_without_auth(self, client, test_user, test_project, db_session):
        """测试未认证更新考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.put(f"/api/v1/exams/{exam.id}", json={
            "name": "新名称"
        })
        
        assert response.status_code == 403


# ===== 考试删除测试 =====

class TestDeleteExam:
    """测试删除考试功能"""

    def test_delete_exam_success(self, client, auth_headers, test_user, test_project, db_session):
        """测试成功删除考试（管理员）"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="待删除考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.delete(f"/api/v1/exams/{exam.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # 验证考试已被删除
        deleted_exam = db_session.query(ExamSchedule).filter(ExamSchedule.id == exam.id).first()
        assert deleted_exam is None

    def test_delete_exam_non_admin_forbidden(self, client, viewer_headers, test_user, test_project, db_session):
        """测试非管理员删除考试被拒绝"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.delete(f"/api/v1/exams/{exam.id}", headers=viewer_headers)
        
        assert response.status_code == 403

    def test_delete_exam_not_found(self, client, auth_headers):
        """测试删除不存在的考试"""
        response = client.delete("/api/v1/exams/non-existent-id", headers=auth_headers)
        
        assert response.status_code == 404

    def test_delete_exam_cascades_reminders(self, client, auth_headers, test_user, test_project, db_session):
        """测试删除考试级联删除提醒"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="带提醒的考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 创建提醒
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=0,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()
        
        # 删除考试
        response = client.delete(f"/api/v1/exams/{exam.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # 验证提醒也被删除
        reminders = db_session.query(ExamReminder).filter(ExamReminder.exam_id == exam.id).all()
        assert len(reminders) == 0

    def test_delete_exam_without_auth(self, client, test_user, test_project, db_session):
        """测试未认证删除考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.delete(f"/api/v1/exams/{exam.id}")
        
        assert response.status_code == 403


# ===== 即将开始的考试测试 =====

class TestGetUpcomingExams:
    """测试获取即将开始的考试功能"""

    def test_get_upcoming_exams_success(self, client, auth_headers, test_user, test_project, db_session):
        """测试成功获取即将开始的考试"""
        # 创建一个10分钟后开始的考试
        start_time = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="即将开始的考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            reminder_15min=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 创建提醒记录
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=0,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()
        
        response = client.get("/api/v1/exams/upcoming", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 应该包含即将开始的考试

    def test_get_upcoming_exams_empty(self, client, auth_headers):
        """测试获取空的即将开始考试列表"""
        response = client.get("/api/v1/exams/upcoming", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]

    def test_get_upcoming_exams_without_auth(self, client):
        """测试未认证获取即将开始的考试"""
        response = client.get("/api/v1/exams/upcoming")
        
        assert response.status_code == 403


# ===== 关闭提醒测试 =====

class TestDismissReminder:
    """测试关闭提醒功能"""

    def test_dismiss_reminder_success(self, client, auth_headers, test_user, test_project, db_session):
        """测试成功关闭提醒"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="提醒测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 创建提醒
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=0,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()
        
        response = client.post(f"/api/v1/exams/{exam.id}/dismiss", json={
            "reminder_type": "15min"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["dismissed_count"] == 1

    def test_dismiss_reminder_all_types(self, client, auth_headers, test_user, test_project, db_session):
        """测试关闭所有类型的提醒"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="多提醒考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 创建多个提醒
        for reminder_type in ["15min", "5min", "start"]:
            reminder = ExamReminder(
                exam_id=exam.id,
                user_id=test_user.id,
                reminder_type=reminder_type,
                is_triggered=0,
                is_dismissed=0
            )
            db_session.add(reminder)
        db_session.commit()
        
        # 关闭所有提醒
        response = client.post(f"/api/v1/exams/{exam.id}/dismiss", json={
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["dismissed_count"] == 3

    def test_dismiss_reminder_exam_not_found(self, client, auth_headers):
        """测试为不存在的考试关闭提醒"""
        response = client.post("/api/v1/exams/non-existent-id/dismiss", json={
            "reminder_type": "15min"
        }, headers=auth_headers)
        
        assert response.status_code == 404

    def test_dismiss_reminder_invalid_type(self, client, auth_headers, test_user, test_project, db_session):
        """测试关闭无效类型的提醒"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.post(f"/api/v1/exams/{exam.id}/dismiss", json={
            "reminder_type": "invalid_type"
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_dismiss_reminder_without_auth(self, client, test_user, test_project, db_session):
        """测试未认证关闭提醒"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        response = client.post(f"/api/v1/exams/{exam.id}/dismiss", json={
            "reminder_type": "15min"
        })
        
        assert response.status_code == 403


# ===== 请求模型验证测试 =====

class TestExamRequestModels:
    """测试考试请求模型"""

    def test_exam_create_valid(self):
        """测试有效考试创建"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        request = ExamCreate(
            name="测试考试",
            description="考试描述",
            start_time=start_time,
            end_time=end_time,
            project_id="project-id-123",
            reminder_15min=1,
            reminder_5min=1,
            reminder_start=1
        )
        assert request.name == "测试考试"
        assert request.reminder_15min == 1

    def test_exam_create_without_optional_fields(self):
        """测试考试创建不带可选字段"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        request = ExamCreate(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id="project-id-123"
        )
        assert request.name == "测试考试"
        assert request.description is None
        assert request.reminder_15min == 1  # 默认值

    def test_exam_update_valid(self):
        """测试有效考试更新"""
        request = ExamUpdate(name="新名称", description="新描述", reminder_15min=0)
        assert request.name == "新名称"
        assert request.reminder_15min == 0

    def test_exam_update_partial(self):
        """测试部分考试更新"""
        request = ExamUpdate(name="仅名称")
        assert request.name == "仅名称"
        assert request.description is None

    def test_exam_response_model(self):
        """测试考试响应模型"""
        response = ExamResponse(
            id="exam-id-123",
            name="测试考试",
            description="考试描述",
            start_time="2024-01-01T09:00:00Z",
            end_time="2024-01-01T11:00:00Z",
            project_id="project-id-123",
            project_name="测试项目",
            status="upcoming",
            reminder_15min=1,
            reminder_5min=1,
            reminder_start=1,
            created_by="user-id-123",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        assert response.id == "exam-id-123"
        assert response.name == "测试考试"
        assert response.status == "upcoming"

    def test_exam_dismiss_request_valid(self):
        """测试有效关闭提醒请求"""
        request = ExamDismissRequest(reminder_type="15min")
        assert request.reminder_type == "15min"

    def test_exam_dismiss_request_all(self):
        """测试关闭所有提醒请求"""
        request = ExamDismissRequest()
        assert request.reminder_type is None

    def test_upcoming_exam_item_model(self):
        """测试即将开始考试项模型"""
        item = UpcomingExamItem(
            exam_id="exam-id-123",
            exam_name="即将开始的考试",
            description="考试描述",
            start_time="2024-01-01T09:00:00Z",
            end_time="2024-01-01T11:00:00Z",
            project_id="project-id-123",
            project_name="测试项目",
            minutes_until_start=10.5,
            reminder_type="15min",
            reminder_id="reminder-id-123"
        )
        assert item.exam_id == "exam-id-123"
        assert item.minutes_until_start == 10.5


# ===== 考试状态模型测试 =====

class TestExamStatusModel:
    """测试考试状态模型"""

    def test_exam_status_enum_values(self):
        """测试考试状态枚举值"""
        assert ExamStatus.upcoming.value == "upcoming"
        assert ExamStatus.ongoing.value == "ongoing"
        assert ExamStatus.expired.value == "expired"

    def test_exam_schedule_update_status_upcoming(self, test_user, test_project, db_session):
        """测试更新考试状态为即将开始"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="即将开始考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        exam.update_status()
        assert exam.status == ExamStatus.upcoming.value

    def test_exam_schedule_is_expired(self, test_user, test_project, db_session):
        """测试检查考试是否已过期"""
        start_time = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
        end_time = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="已过期考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.expired.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        assert exam.is_expired() is True
        assert exam.is_upcoming() is False
        assert exam.is_ongoing() is False

    def test_exam_schedule_get_time_until_start(self, test_user, test_project, db_session):
        """测试获取距离考试开始的分钟数"""
        start_time = (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="30分钟后开始的考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        minutes = exam.get_time_until_start()
        # 应该接近30分钟（允许一定误差）
        assert 25 < minutes < 35

    def test_exam_schedule_get_time_until_end(self, test_user, test_project, db_session):
        """测试获取距离考试结束的分钟数"""
        start_time = (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="30分钟后结束的考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.ongoing.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        minutes = exam.get_time_until_end()
        # 应该接近30分钟（允许一定误差）
        assert 25 < minutes < 35


# ===== 考试提醒模型测试 =====

class TestExamReminderModel:
    """测试考试提醒模型"""

    def test_exam_reminder_mark_triggered(self, test_user, test_project, db_session):
        """测试标记提醒为已触发"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=0,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()
        
        reminder.mark_triggered()
        assert reminder.is_triggered == 1
        assert reminder.triggered_at is not None

    def test_exam_reminder_mark_dismissed(self, test_user, test_project, db_session):
        """测试标记提醒为已关闭"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()
        
        reminder.mark_dismissed()
        assert reminder.is_dismissed == 1
        assert reminder.dismissed_at is not None

    def test_exam_reminder_is_active(self, test_user, test_project, db_session):
        """测试检查提醒是否处于活动状态"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 已触发但未关闭
        active_reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=0
        )
        # 未触发
        inactive_reminder1 = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="5min",
            is_triggered=0,
            is_dismissed=0
        )
        # 已关闭
        inactive_reminder2 = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="start",
            is_triggered=1,
            is_dismissed=1
        )
        db_session.add_all([active_reminder, inactive_reminder1, inactive_reminder2])
        db_session.commit()
        
        assert active_reminder.is_active() is True
        assert inactive_reminder1.is_active() is False
        assert inactive_reminder2.is_active() is False

    def test_exam_reminder_reset(self, test_user, test_project, db_session):
        """测试重置提醒状态"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=1,
            triggered_at=datetime.utcnow().isoformat() + "Z",
            dismissed_at=datetime.utcnow().isoformat() + "Z"
        )
        db_session.add(reminder)
        db_session.commit()
        
        reminder.reset()
        assert reminder.is_triggered == 0
        assert reminder.is_dismissed == 0
        assert reminder.triggered_at is None
        assert reminder.dismissed_at is None


# ===== 边界情况测试 =====

class TestExamEdgeCases:
    """考试边界情况测试"""

    def test_create_exam_with_unicode_name(self, client, auth_headers, test_project):
        """测试使用Unicode名称创建考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "数学考试📝",
            "description": "Unicode描述",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 201
        assert response.json()["data"]["name"] == "数学考试📝"

    def test_create_exam_with_special_characters_in_name(self, client, auth_headers, test_project):
        """测试考试名称包含特殊字符"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "考试-2024_期末.v1",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 201

    def test_create_exam_with_very_long_name(self, client, auth_headers, test_project):
        """测试创建考试名称过长"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "a" * 101,  # 超过100字符限制
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_exam_with_very_long_description(self, client, auth_headers, test_project):
        """测试创建考试描述过长"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        response = client.post("/api/v1/exams", json={
            "name": "正常名称",
            "description": "a" * 501,  # 超过500字符限制
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_update_exam_with_same_name(self, client, auth_headers, test_user, test_project, db_session):
        """测试更新考试为相同名称"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="相同名称",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 更新为相同名称应该成功
        response = client.put(f"/api/v1/exams/{exam.id}", json={
            "name": "相同名称"
        }, headers=auth_headers)
        
        assert response.status_code == 200

    def test_list_exams_empty_result(self, client, auth_headers):
        """测试获取空考试列表"""
        response = client.get("/api/v1/exams", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] >= 0
        assert isinstance(data["data"]["items"], list)


# ===== 集成测试 =====

class TestExamIntegration:
    """考试集成测试"""

    def test_create_list_get_update_delete_flow(self, client, auth_headers, test_project):
        """测试完整的考试CRUD流程"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
        
        # 创建考试
        create_response = client.post("/api/v1/exams", json={
            "name": "完整流程考试",
            "description": "完整流程描述",
            "start_time": start_time,
            "end_time": end_time,
            "project_id": test_project.id
        }, headers=auth_headers)
        
        assert create_response.status_code == 201
        exam_id = create_response.json()["data"]["id"]
        
        # 获取考试列表
        list_response = client.get("/api/v1/exams", headers=auth_headers)
        assert list_response.status_code == 200
        exam_ids = [e["id"] for e in list_response.json()["data"]["items"]]
        assert exam_id in exam_ids
        
        # 获取考试详情
        get_response = client.get(f"/api/v1/exams/{exam_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["data"]["name"] == "完整流程考试"
        
        # 更新考试
        update_response = client.put(f"/api/v1/exams/{exam_id}", json={
            "name": "更新后的考试"
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["data"]["name"] == "更新后的考试"
        
        # 删除考试
        delete_response = client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)
        assert delete_response.status_code == 204
        
        # 验证考试已删除
        get_deleted_response = client.get(f"/api/v1/exams/{exam_id}", headers=auth_headers)
        assert get_deleted_response.status_code == 404

    def test_multiple_exams_pagination(self, client, auth_headers, test_user, test_project, db_session):
        """测试多个考试的分页"""
        # 创建15个考试
        for i in range(15):
            start_time = (datetime.utcnow() + timedelta(days=i+1)).isoformat() + "Z"
            end_time = (datetime.utcnow() + timedelta(days=i+1, hours=2)).isoformat() + "Z"
            exam = ExamSchedule(
                name=f"分页考试{i+1:02d}",
                start_time=start_time,
                end_time=end_time,
                project_id=test_project.id,
                status=ExamStatus.upcoming.value,
                created_by=test_user.id
            )
            db_session.add(exam)
        db_session.commit()
        
        # 获取第一页
        page1 = client.get("/api/v1/exams?page=1&page_size=10", headers=auth_headers)
        assert page1.status_code == 200
        assert len(page1.json()["data"]["items"]) == 10
        
        # 获取第二页
        page2 = client.get("/api/v1/exams?page=2&page_size=10", headers=auth_headers)
        assert page2.status_code == 200
        assert len(page2.json()["data"]["items"]) >= 5

    def test_exam_reminder_workflow(self, client, auth_headers, test_user, test_project, db_session):
        """测试考试提醒完整工作流"""
        # 创建一个10分钟后开始的考试
        start_time = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        
        exam = ExamSchedule(
            name="提醒工作流考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            reminder_15min=1,
            reminder_5min=1,
            reminder_start=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        
        # 创建提醒记录
        for reminder_type in ["15min", "5min", "start"]:
            reminder = ExamReminder(
                exam_id=exam.id,
                user_id=test_user.id,
                reminder_type=reminder_type,
                is_triggered=0,
                is_dismissed=0
            )
            db_session.add(reminder)
        db_session.commit()
        
        # 获取即将开始的考试
        upcoming_response = client.get("/api/v1/exams/upcoming", headers=auth_headers)
        assert upcoming_response.status_code == 200
        
        # 关闭15分钟提醒
        dismiss_response = client.post(f"/api/v1/exams/{exam.id}/dismiss", json={
            "reminder_type": "15min"
        }, headers=auth_headers)
        assert dismiss_response.status_code == 200
        assert dismiss_response.json()["data"]["dismissed_count"] == 1
        
        # 关闭所有提醒
        dismiss_all_response = client.post(f"/api/v1/exams/{exam.id}/dismiss", json={
        }, headers=auth_headers)
        assert dismiss_all_response.status_code == 200
        assert dismiss_all_response.json()["data"]["dismissed_count"] == 2  # 还剩2个
