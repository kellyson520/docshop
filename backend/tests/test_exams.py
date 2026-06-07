"""
考试安排模块 API 测试

测试考试相关的 API 端点，包括创建、列表、详情、更新、删除和提醒功能。
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from app.models.exam_schedule import ExamSchedule, ExamReminder, ExamStatus
from app.models.project import Project


class TestExamCreate:
    """考试创建测试"""

    def test_create_exam_success(self, client, auth_headers, db_session, test_user):
        """测试创建考试成功"""
        # 先创建项目
        project = Project(name="考试测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 计算考试时间
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "期末考试",
                "description": "这是期末考试",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id,
                "reminder_15min": 1,
                "reminder_5min": 1,
                "reminder_start": 1
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "期末考试"
        assert data["data"]["project_id"] == project.id
        assert data["data"]["status"] == ExamStatus.upcoming.value

        # 验证提醒记录已创建
        exam_id = data["data"]["id"]
        reminders = db_session.query(ExamReminder).filter(ExamReminder.exam_id == exam_id).all()
        assert len(reminders) == 3  # 15min, 5min, start

    def test_create_exam_non_admin(self, client, viewer_headers, db_session, test_user_viewer):
        """测试非管理员创建考试失败"""
        # 先创建项目
        project = Project(name="普通用户项目", description="描述", owner_id=test_user_viewer.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        response = client.post(
            "/api/v1/exams",
            headers=viewer_headers,
            json={
                "name": "期末考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )

        # 非管理员应返回 403
        assert response.status_code == 403

    def test_create_exam_invalid_project(self, client, auth_headers):
        """测试无效项目ID创建考试"""
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "期末考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": "00000000-0000-0000-0000-000000000000"  # 有效格式但不存在的ID
            }
        )

        # 项目不存在应返回 404
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001  # ResourceNotFound

    def test_create_exam_end_before_start(self, client, auth_headers, db_session, test_user):
        """测试结束时间早于开始时间"""
        project = Project(name="时间测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 结束时间早于开始时间
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"

        response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "时间错误考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )

        # Pydantic 校验失败返回 422
        assert response.status_code == 422

    def test_create_exam_duplicate_name(self, client, auth_headers, db_session, test_user):
        """测试同一项目下同名考试"""
        project = Project(name="重复名称项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        # 创建第一个考试
        exam1 = ExamSchedule(
            name="同名考试",
            description="第一个",
            start_time=start_time,
            end_time=end_time,
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam1)
        db_session.commit()

        # 尝试创建同名考试
        response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "同名考试",
                "description": "第二个",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )

        # 重复名称应返回 400 (ValidationError)
        assert response.status_code == 400

    def test_create_exam_db_error(self, client, auth_headers, db_session, test_user):
        """测试创建考试时数据库错误（行430-445）"""
        project = Project(name="数据库错误考试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        with patch.object(db_session, "flush", side_effect=SQLAlchemyError("DB error")):
            response = client.post(
                "/api/v1/exams",
                headers=auth_headers,
                json={
                    "name": "数据库错误考试",
                    "description": "描述",
                    "start_time": start_time,
                    "end_time": end_time,
                    "project_id": project.id
                }
            )

        assert response.status_code == 500

    def test_create_exam_generic_error(self, client, auth_headers, db_session, test_user):
        """测试创建考试时通用错误（行437-445）"""
        project = Project(name="通用错误考试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        with patch("app.routers.exams._create_reminder_records", side_effect=RuntimeError("Reminder error")):
            response = client.post(
                "/api/v1/exams",
                headers=auth_headers,
                json={
                    "name": "通用错误考试",
                    "description": "描述",
                    "start_time": start_time,
                    "end_time": end_time,
                    "project_id": project.id
                }
            )

        assert response.status_code == 500


class TestExamList:
    """考试列表测试"""

    def test_get_exam_list_success(self, client, auth_headers, db_session, test_user):
        """测试获取考试列表成功"""
        # 创建项目和考试
        project = Project(name="列表测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        for i in range(5):
            exam = ExamSchedule(
                name=f"考试{i+1}",
                description=f"描述{i+1}",
                start_time=(datetime.utcnow() + timedelta(days=i+1)).isoformat() + "Z",
                end_time=(datetime.utcnow() + timedelta(days=i+1, hours=2)).isoformat() + "Z",
                project_id=project.id,
                created_by=test_user.id
            )
            db_session.add(exam)
        db_session.commit()

        response = client.get("/api/v1/exams", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) >= 5
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]

    def test_get_exam_list_pagination(self, client, auth_headers, db_session, test_user):
        """测试考试列表分页"""
        project = Project(name="分页测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建10个考试
        for i in range(10):
            exam = ExamSchedule(
                name=f"分页考试{i+1}",
                description=f"描述{i+1}",
                start_time=(datetime.utcnow() + timedelta(days=i+1)).isoformat() + "Z",
                end_time=(datetime.utcnow() + timedelta(days=i+1, hours=2)).isoformat() + "Z",
                project_id=project.id,
                created_by=test_user.id
            )
            db_session.add(exam)
        db_session.commit()

        # 测试第一页
        response = client.get("/api/v1/exams?page=1&page_size=5", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 5
        assert data["data"]["page"] == 1

        # 测试第二页
        response = client.get("/api/v1/exams?page=2&page_size=5", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 5
        assert data["data"]["page"] == 2

    def test_get_exam_list_status_filter(self, client, auth_headers, db_session, test_user):
        """测试状态筛选"""
        project = Project(name="状态筛选项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建不同状态的考试
        # upcoming 考试
        exam_upcoming = ExamSchedule(
            name="即将开始考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id
        )
        db_session.add(exam_upcoming)

        # expired 考试
        exam_expired = ExamSchedule(
            name="已结束考试",
            description="描述",
            start_time=(datetime.utcnow() - timedelta(days=2)).isoformat() + "Z",
            end_time=(datetime.utcnow() - timedelta(days=1)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.expired.value,
            created_by=test_user.id
        )
        db_session.add(exam_expired)
        db_session.commit()

        # 筛选 upcoming
        response = client.get("/api/v1/exams?status=upcoming", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert all(item["status"] == ExamStatus.upcoming.value for item in data["data"]["items"])

        # 筛选 expired
        response = client.get("/api/v1/exams?status=expired", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert all(item["status"] == ExamStatus.expired.value for item in data["data"]["items"])

    def test_get_exam_list_keyword_search(self, client, auth_headers, db_session, test_user):
        """测试关键词搜索"""
        project = Project(name="搜索测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建不同名称的考试
        exam1 = ExamSchedule(
            name="数学期末考试",
            description="描述1",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        exam2 = ExamSchedule(
            name="英语期中考试",
            description="描述2",
            start_time=(datetime.utcnow() + timedelta(days=2)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=2, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add_all([exam1, exam2])
        db_session.commit()

        # 搜索"数学"
        response = client.get("/api/v1/exams?keyword=数学", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert any("数学" in item["name"] for item in data["data"]["items"])

    def test_get_exam_list_auto_status_update(self, client, auth_headers, db_session, test_user):
        """测试自动状态更新"""
        project = Project(name="状态更新项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建一个应该变为 ongoing 的考试（已开始但未结束）
        exam = ExamSchedule(
            name="进行中考试",
            description="描述",
            start_time=(datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.upcoming.value,  # 初始状态为 upcoming
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()

        # 获取列表，应该自动更新状态
        response = client.get("/api/v1/exams", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0

        # 检查考试状态是否已更新
        exam_item = next((item for item in data["data"]["items"] if item["id"] == exam.id), None)
        if exam_item:
            # 状态应该被自动更新为 ongoing
            assert exam_item["status"] == ExamStatus.ongoing.value

    def test_get_exam_list_project_filter(self, client, auth_headers, db_session, test_user):
        """测试项目ID筛选（行250）"""
        project1 = Project(name="项目A", description="描述", owner_id=test_user.id)
        project2 = Project(name="项目B", description="描述", owner_id=test_user.id)
        db_session.add_all([project1, project2])
        db_session.commit()

        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        exam1 = ExamSchedule(
            name="项目A考试", description="描述",
            start_time=start_time, end_time=end_time,
            project_id=project1.id, created_by=test_user.id
        )
        exam2 = ExamSchedule(
            name="项目B考试", description="描述",
            start_time=start_time, end_time=end_time,
            project_id=project2.id, created_by=test_user.id
        )
        db_session.add_all([exam1, exam2])
        db_session.commit()

        response = client.get(f"/api/v1/exams?project_id={project1.id}", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert all(item["project_id"] == project1.id for item in data["data"]["items"])

    def test_get_exam_list_error(self, client, auth_headers, db_session, test_user):
        """测试获取考试列表时错误（行348-352）"""
        # 创建考试数据，确保 _update_exam_status 会被调用
        project = Project(name="错误列表项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="错误列表考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()

        # Mock _update_exam_status 来触发列表查询中的异常
        with patch("app.routers.exams._update_exam_status", side_effect=RuntimeError("Status error")):
            response = client.get("/api/v1/exams", headers=auth_headers)

        assert response.status_code == 500


class TestExamDetail:
    """考试详情测试"""

    def test_get_exam_detail_success(self, client, auth_headers, db_session, test_user):
        """测试获取考试详情成功"""
        project = Project(name="详情测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="详情考试",
            description="详细描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        response = client.get(f"/api/v1/exams/{exam.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "详情考试"
        assert data["data"]["id"] == exam.id
        assert "time_until_start" in data["data"]
        assert "time_until_end" in data["data"]
        assert "is_expired" in data["data"]
        assert "is_upcoming" in data["data"]
        assert "is_ongoing" in data["data"]

    def test_get_exam_detail_not_found(self, client, auth_headers):
        """测试获取不存在的考试详情"""
        response = client.get("/api/v1/exams/non-existent-id", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001  # ResourceNotFound

    def test_get_exam_detail_auto_status_update(self, client, auth_headers, db_session, test_user):
        """测试详情获取时自动状态更新"""
        project = Project(name="状态更新详情项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建一个应该变为 expired 的考试
        exam = ExamSchedule(
            name="已过期考试",
            description="描述",
            start_time=(datetime.utcnow() - timedelta(days=2)).isoformat() + "Z",
            end_time=(datetime.utcnow() - timedelta(days=1)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.upcoming.value,  # 初始状态
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        response = client.get(f"/api/v1/exams/{exam.id}", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        # 状态应该被自动更新为 expired
        assert data["data"]["status"] == ExamStatus.expired.value
        assert data["data"]["is_expired"] is True

    def test_get_exam_detail_error(self, client, auth_headers, db_session, test_user):
        """测试获取考试详情时错误（行603-607）"""
        project = Project(name="详情错误项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="详情错误考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        with patch("app.routers.exams._update_exam_status", side_effect=RuntimeError("Status error")):
            response = client.get(f"/api/v1/exams/{exam.id}", headers=auth_headers)

        assert response.status_code == 500


class TestExamUpdate:
    """考试更新测试"""

    def test_update_exam_success(self, client, auth_headers, db_session, test_user):
        """测试更新考试成功"""
        project = Project(name="更新测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="原考试名称",
            description="原描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        new_start = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"
        new_end = (datetime.utcnow() + timedelta(days=2, hours=2)).isoformat() + "Z"

        response = client.put(
            f"/api/v1/exams/{exam.id}",
            headers=auth_headers,
            json={
                "name": "新考试名称",
                "description": "新描述",
                "start_time": new_start,
                "end_time": new_end,
                "reminder_15min": 0,
                "reminder_5min": 0,
                "reminder_start": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "新考试名称"
        assert data["data"]["description"] == "新描述"
        assert data["data"]["reminder_15min"] == 0

    def test_update_exam_non_admin(self, client, viewer_headers, db_session, test_user_viewer):
        """测试非管理员更新考试失败"""
        project = Project(name="普通用户项目2", description="描述", owner_id=test_user_viewer.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="普通用户考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user_viewer.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        response = client.put(
            f"/api/v1/exams/{exam.id}",
            headers=viewer_headers,
            json={"name": "新名称"}
        )

        assert response.status_code == 403

    def test_update_exam_not_found(self, client, auth_headers):
        """测试更新不存在的考试"""
        response = client.put(
            "/api/v1/exams/non-existent-id",
            headers=auth_headers,
            json={"name": "新名称"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001  # ResourceNotFound

    def test_update_exam_partial(self, client, auth_headers, db_session, test_user):
        """测试部分更新考试"""
        project = Project(name="部分更新项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        original_start = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        exam = ExamSchedule(
            name="部分更新考试",
            description="原描述",
            start_time=original_start,
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 只更新名称
        response = client.put(
            f"/api/v1/exams/{exam.id}",
            headers=auth_headers,
            json={"name": "仅更新名称"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "仅更新名称"
        assert data["data"]["description"] == "原描述"  # 未改变
        assert data["data"]["start_time"] == original_start  # 未改变

    def test_update_exam_name_conflict(self, client, auth_headers, db_session, test_user):
        """测试更新考试时名称冲突（行641）"""
        project = Project(name="名称冲突项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        end_time = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"

        exam1 = ExamSchedule(
            name="考试A", description="描述",
            start_time=start_time, end_time=end_time,
            project_id=project.id, created_by=test_user.id
        )
        exam2 = ExamSchedule(
            name="考试B", description="描述",
            start_time=start_time, end_time=end_time,
            project_id=project.id, created_by=test_user.id
        )
        db_session.add_all([exam1, exam2])
        db_session.commit()

        # 将 exam2 的名称改为 exam1 的名称
        response = client.put(
            f"/api/v1/exams/{exam2.id}",
            headers=auth_headers,
            json={"name": "考试A"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 40001

    def test_update_exam_db_error(self, client, auth_headers, db_session, test_user):
        """测试更新考试时数据库错误（行701-712）"""
        project = Project(name="数据库错误更新考试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="数据库错误更新考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("DB error")):
            response = client.put(
                f"/api/v1/exams/{exam.id}",
                headers=auth_headers,
                json={"name": "新名称"}
            )

        assert response.status_code == 500

    def test_update_exam_generic_error(self, client, auth_headers, db_session, test_user):
        """测试更新考试时通用错误（行708-712）"""
        project = Project(name="通用错误更新考试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="通用错误更新考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # Mock db.refresh 来触发通用异常
        with patch.object(db_session, "refresh", side_effect=RuntimeError("Refresh error")):
            response = client.put(
                f"/api/v1/exams/{exam.id}",
                headers=auth_headers,
                json={"name": "新名称"}
            )

        assert response.status_code == 500


class TestExamDelete:
    """考试删除测试"""

    def test_delete_exam_success(self, client, auth_headers, db_session, test_user):
        """测试删除考试成功"""
        project = Project(name="删除测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="待删除考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 创建关联的提醒记录
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min"
        )
        db_session.add(reminder)
        db_session.commit()

        exam_id = exam.id

        response = client.delete(f"/api/v1/exams/{exam.id}", headers=auth_headers)

        # 删除返回 204 No Content
        assert response.status_code == 204

        # 验证考试已删除
        deleted_exam = db_session.query(ExamSchedule).filter(ExamSchedule.id == exam_id).first()
        assert deleted_exam is None

        # 验证关联的提醒记录也已级联删除
        deleted_reminders = db_session.query(ExamReminder).filter(ExamReminder.exam_id == exam_id).all()
        assert len(deleted_reminders) == 0

    def test_delete_exam_non_admin(self, client, viewer_headers, db_session, test_user_viewer):
        """测试非管理员删除考试失败"""
        project = Project(name="普通用户项目3", description="描述", owner_id=test_user_viewer.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="普通用户考试2",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user_viewer.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        response = client.delete(f"/api/v1/exams/{exam.id}", headers=viewer_headers)

        assert response.status_code == 403

    def test_delete_exam_not_found(self, client, auth_headers):
        """测试删除不存在的考试"""
        response = client.delete("/api/v1/exams/non-existent-id", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001  # ResourceNotFound

    def test_delete_exam_db_error(self, client, auth_headers, db_session, test_user):
        """测试删除考试时数据库错误（行756-767）"""
        project = Project(name="数据库错误删除考试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="数据库错误删除考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        with patch.object(db_session, "delete", side_effect=SQLAlchemyError("DB error")):
            response = client.delete(f"/api/v1/exams/{exam.id}", headers=auth_headers)

        assert response.status_code == 500

    def test_delete_exam_generic_error(self, client, auth_headers, db_session, test_user):
        """测试删除考试时通用错误（行763-767）"""
        project = Project(name="通用错误删除考试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="通用错误删除考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # Mock db.delete 来触发非 SQLAlchemyError 异常
        original_delete = db_session.delete
        call_count = [0]

        def side_effect_delete(item):
            call_count[0] += 1
            original_delete(item)
            if call_count[0] == 1:
                raise RuntimeError("Generic error")

        with patch.object(db_session, "delete", side_effect=side_effect_delete):
            response = client.delete(f"/api/v1/exams/{exam.id}", headers=auth_headers)

        assert response.status_code == 500


class TestExamUpcoming:
    """即将开始考试提醒测试"""

    def test_upcoming_15min_reminder(self, client, auth_headers, db_session, test_user):
        """测试考前15分钟提醒"""
        project = Project(name="15分钟提醒项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建10分钟后开始的考试
        exam = ExamSchedule(
            name="15分钟提醒考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            reminder_15min=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

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

        # 获取即将开始的考试
        response = client.get("/api/v1/exams/upcoming", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 应该包含15分钟提醒
        assert any(item["reminder_type"] == "15min" for item in data["data"]["items"])

    def test_upcoming_5min_reminder(self, client, auth_headers, db_session, test_user):
        """测试考前5分钟提醒"""
        project = Project(name="5分钟提醒项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建3分钟后开始的考试
        exam = ExamSchedule(
            name="5分钟提醒考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=3)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            reminder_5min=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 创建提醒记录
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="5min",
            is_triggered=0,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()

        response = client.get("/api/v1/exams/upcoming", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 应该包含5分钟提醒
        assert any(item["reminder_type"] == "5min" for item in data["data"]["items"])

    def test_upcoming_start_reminder(self, client, auth_headers, db_session, test_user):
        """测试开始时提醒"""
        project = Project(name="开始提醒项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建已经开始的考试（1分钟前开始）
        exam = ExamSchedule(
            name="开始提醒考试",
            description="描述",
            start_time=(datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            reminder_start=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 创建提醒记录
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="start",
            is_triggered=0,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()

        response = client.get("/api/v1/exams/upcoming", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 应该包含开始提醒
        assert any(item["reminder_type"] == "start" for item in data["data"]["items"])

    def test_upcoming_dismissed_no_reminder(self, client, auth_headers, db_session, test_user):
        """测试已关闭的提醒不再提醒"""
        project = Project(name="关闭提醒项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建10分钟后开始的考试
        exam = ExamSchedule(
            name="关闭提醒考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            reminder_15min=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 创建已关闭的提醒记录
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=1  # 已关闭
        )
        db_session.add(reminder)
        db_session.commit()

        response = client.get("/api/v1/exams/upcoming", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 不应该包含已关闭的提醒
        assert not any(item["exam_id"] == exam.id for item in data["data"]["items"])

    def test_get_upcoming_exams_error(self, client, auth_headers, db_session, test_user):
        """测试获取即将开始的考试时错误（行485-489）"""
        # Mock _get_upcoming_reminders 来触发异常
        with patch("app.routers.exams._get_upcoming_reminders", side_effect=RuntimeError("Upcoming error")):
            response = client.get("/api/v1/exams/upcoming", headers=auth_headers)

        assert response.status_code == 500


class TestExamDismiss:
    """关闭提醒测试"""

    def test_dismiss_reminder_success(self, client, auth_headers, db_session, test_user):
        """测试关闭提醒成功"""
        project = Project(name="关闭提醒测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="关闭提醒考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 创建提醒记录
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()

        response = client.post(
            f"/api/v1/exams/{exam.id}/dismiss",
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["dismissed_count"] >= 1

        # 验证提醒已关闭
        db_session.refresh(reminder)
        assert reminder.is_dismissed == 1

    def test_dismiss_reminder_already_dismissed(self, client, auth_headers, db_session, test_user):
        """测试重复关闭提醒"""
        project = Project(name="重复关闭项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="重复关闭考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 创建已关闭的提醒记录
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=1  # 已关闭
        )
        db_session.add(reminder)
        db_session.commit()

        # 再次关闭应该返回 404（没有活动提醒）
        response = client.post(
            f"/api/v1/exams/{exam.id}/dismiss",
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001  # ResourceNotFound

    def test_dismiss_specific_reminder_type(self, client, auth_headers, db_session, test_user):
        """测试关闭特定类型的提醒"""
        project = Project(name="特定类型关闭项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="特定类型关闭考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        # 创建多个提醒记录
        reminder_15min = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=0
        )
        reminder_5min = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="5min",
            is_triggered=1,
            is_dismissed=0
        )
        db_session.add_all([reminder_15min, reminder_5min])
        db_session.commit()

        # 只关闭15分钟提醒
        response = client.post(
            f"/api/v1/exams/{exam.id}/dismiss",
            headers=auth_headers,
            json={"reminder_type": "15min"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["dismissed_count"] == 1

        # 验证只有15分钟提醒被关闭
        db_session.refresh(reminder_15min)
        db_session.refresh(reminder_5min)
        assert reminder_15min.is_dismissed == 1
        assert reminder_5min.is_dismissed == 0

    def test_dismiss_reminder_not_found(self, client, auth_headers):
        """测试关闭不存在的考试的提醒"""
        response = client.post(
            "/api/v1/exams/non-existent-id/dismiss",
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001

    def test_dismiss_reminder_db_error(self, client, auth_headers, db_session, test_user):
        """测试关闭提醒时数据库错误（行557-568）"""
        project = Project(name="数据库错误关闭提醒项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="数据库错误关闭提醒考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()

        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("DB error")):
            response = client.post(
                f"/api/v1/exams/{exam.id}/dismiss",
                headers=auth_headers,
                json={}
            )

        assert response.status_code == 500

    def test_dismiss_reminder_generic_error(self, client, auth_headers, db_session, test_user):
        """测试关闭提醒时通用错误（行564-568）"""
        project = Project(name="通用错误关闭提醒项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="通用错误关闭提醒考试",
            description="描述",
            start_time=(datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z",
            end_time=(datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=1,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()

        # Mock mark_dismissed 来触发通用异常
        with patch("app.routers.exams.ExamReminder.mark_dismissed", side_effect=RuntimeError("Mark error")):
            response = client.post(
                f"/api/v1/exams/{exam.id}/dismiss",
                headers=auth_headers,
                json={}
            )

        assert response.status_code == 500
