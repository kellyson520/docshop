"""
考试安排端到端测试

测试完整的考试业务流程，包括生命周期管理、提醒流程和状态转换。
"""
import pytest
from datetime import datetime, timedelta
from app.utils.time import utc_now, utc_now_iso
from app.models.exam_schedule import ExamSchedule, ExamReminder, ExamStatus
from app.models.project import Project


class TestExamLifecycle:
    """考试完整生命周期测试"""

    def test_complete_exam_lifecycle(self, client, auth_headers, db_session, test_user):
        """
        测试完整的考试生命周期

        流程：
        1. 创建项目
        2. 创建考试
        3. 查看考试详情
        4. 更新考试
        5. 删除考试
        """
        # 1. 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "生命周期测试项目",
                "description": "用于测试考试生命周期"
            }
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # 2. 创建考试
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "生命周期测试考试",
                "description": "这是一个测试考试",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_id,
                "reminder_15min": 1,
                "reminder_5min": 1,
                "reminder_start": 1
            }
        )
        assert create_response.status_code == 201
        exam_id = create_response.json()["data"]["id"]
        assert create_response.json()["data"]["name"] == "生命周期测试考试"

        # 3. 查看考试详情
        detail_response = client.get(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers
        )
        assert detail_response.status_code == 200
        detail_data = detail_response.json()["data"]
        assert detail_data["id"] == exam_id
        assert detail_data["project_id"] == project_id
        assert "time_until_start" in detail_data

        # 4. 更新考试
        new_start = (utc_now() + timedelta(days=2)).isoformat() + "Z"
        update_response = client.put(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers,
            json={
                "name": "已更新的考试",
                "description": "已更新的描述",
                "start_time": new_start
            }
        )
        assert update_response.status_code == 200
        update_data = update_response.json()["data"]
        assert update_data["name"] == "已更新的考试"
        assert update_data["description"] == "已更新的描述"

        # 5. 删除考试
        delete_response = client.delete(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204

        # 验证已删除
        verify_response = client.get(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers
        )
        assert verify_response.status_code == 404

    def test_exam_reminder_flow(self, client, auth_headers, db_session, test_user):
        """
        测试提醒流程

        流程：
        1. 创建考试
        2. 检查提醒
        3. 关闭提醒
        4. 再次检查无提醒
        """
        # 1. 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "提醒流程测试项目",
                "description": "用于测试提醒流程"
            }
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # 2. 创建考试（10分钟后开始，触发15分钟提醒）
        start_time = (utc_now() + timedelta(minutes=10)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "提醒流程测试考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_id,
                "reminder_15min": 1
            }
        )
        assert create_response.status_code == 201
        exam_id = create_response.json()["data"]["id"]

        # 3. 手动创建提醒记录（模拟系统行为）
        reminder = ExamReminder(
            exam_id=exam_id,
            user_id=test_user.id,
            reminder_type="15min",
            is_triggered=0,
            is_dismissed=0
        )
        db_session.add(reminder)
        db_session.commit()

        # 4. 检查即将开始的考试（应该包含提醒）
        upcoming_response = client.get(
            "/api/v1/exams/upcoming",
            headers=auth_headers
        )
        assert upcoming_response.status_code == 200
        upcoming_data = upcoming_response.json()["data"]
        assert any(item["exam_id"] == exam_id for item in upcoming_data["items"])

        # 5. 关闭提醒
        dismiss_response = client.post(
            f"/api/v1/exams/{exam_id}/dismiss",
            headers=auth_headers,
            json={}
        )
        assert dismiss_response.status_code == 200

        # 6. 再次检查，应该没有提醒
        upcoming_response2 = client.get(
            "/api/v1/exams/upcoming",
            headers=auth_headers
        )
        assert upcoming_response2.status_code == 200
        upcoming_data2 = upcoming_response2.json()["data"]
        assert not any(item["exam_id"] == exam_id for item in upcoming_data2["items"])

        # 清理
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)

    def test_exam_status_transition(self, client, auth_headers, db_session, test_user):
        """
        测试状态转换

        流程：
        1. 创建考试时状态为 upcoming
        2. 时间到达后变为 ongoing
        3. 结束后变为 expired
        """
        # 1. 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "状态转换测试项目",
                "description": "用于测试状态转换"
            }
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # 2. 创建即将开始的考试
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "状态转换测试考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_id
            }
        )
        assert create_response.status_code == 201
        exam_id = create_response.json()["data"]["id"]

        # 3. 验证初始状态为 upcoming
        detail_response = client.get(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers
        )
        assert detail_response.json()["data"]["status"] == ExamStatus.upcoming.value

        # 4. 更新考试时间为进行中（30分钟前开始）
        ongoing_start = (utc_now() - timedelta(minutes=30)).isoformat() + "Z"
        ongoing_end = (utc_now() + timedelta(hours=1)).isoformat() + "Z"

        update_response = client.put(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers,
            json={
                "start_time": ongoing_start,
                "end_time": ongoing_end
            }
        )
        assert update_response.status_code == 200

        # 5. 验证状态变为 ongoing
        detail_response2 = client.get(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers
        )
        assert detail_response2.json()["data"]["status"] == ExamStatus.ongoing.value
        assert detail_response2.json()["data"]["is_ongoing"] is True

        # 6. 更新考试时间为已结束
        expired_start = (utc_now() - timedelta(days=2)).isoformat() + "Z"
        expired_end = (utc_now() - timedelta(days=1)).isoformat() + "Z"

        update_response2 = client.put(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers,
            json={
                "start_time": expired_start,
                "end_time": expired_end
            }
        )
        assert update_response2.status_code == 200

        # 7. 验证状态变为 expired
        detail_response3 = client.get(
            f"/api/v1/exams/{exam_id}",
            headers=auth_headers
        )
        assert detail_response3.json()["data"]["status"] == ExamStatus.expired.value
        assert detail_response3.json()["data"]["is_expired"] is True

        # 清理
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)

    def test_exam_with_project(self, client, auth_headers, db_session, test_user):
        """
        测试关联项目的考试创建和查询

        流程：
        1. 创建项目
        2. 创建多个关联该项目的考试
        3. 按项目筛选考试
        4. 验证项目详情中包含考试
        """
        # 1. 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "关联测试项目",
                "description": "用于测试考试关联"
            }
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # 2. 创建多个关联该项目的考试
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        exam_names = ["数学考试", "英语考试", "物理考试"]
        exam_ids = []

        for name in exam_names:
            create_response = client.post(
                "/api/v1/exams",
                headers=auth_headers,
                json={
                    "name": name,
                    "description": f"{name}描述",
                    "start_time": start_time,
                    "end_time": end_time,
                    "project_id": project_id
                }
            )
            assert create_response.status_code == 201
            exam_ids.append(create_response.json()["data"]["id"])

        # 3. 按项目筛选考试
        list_response = client.get(
            f"/api/v1/exams?project_id={project_id}",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        list_data = list_response.json()["data"]
        assert len(list_data["items"]) == 3

        # 验证所有考试都属于该项目
        for item in list_data["items"]:
            assert item["project_id"] == project_id
            assert item["project_name"] == "关联测试项目"

        # 4. 获取项目详情
        project_detail = client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers
        )
        assert project_detail.status_code == 200

        # 清理
        for exam_id in exam_ids:
            client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)


class TestExamBatchOperations:
    """考试批量操作测试"""

    def test_batch_create_and_list(self, client, auth_headers, db_session, test_user):
        """测试批量创建和列表查询"""
        # 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "批量操作项目",
                "description": "描述"
            }
        )
        project_id = project_response.json()["data"]["id"]

        # 批量创建考试
        exam_ids = []
        for i in range(5):
            start_time = (utc_now() + timedelta(days=i+1)).isoformat() + "Z"
            end_time = (utc_now() + timedelta(days=i+1, hours=2)).isoformat() + "Z"

            response = client.post(
                "/api/v1/exams",
                headers=auth_headers,
                json={
                    "name": f"批量考试{i+1}",
                    "description": f"描述{i+1}",
                    "start_time": start_time,
                    "end_time": end_time,
                    "project_id": project_id
                }
            )
            assert response.status_code == 201
            exam_ids.append(response.json()["data"]["id"])

        # 验证列表
        list_response = client.get("/api/v1/exams", headers=auth_headers)
        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] >= 5

        # 清理
        for exam_id in exam_ids:
            client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)

    def test_pagination_with_multiple_pages(self, client, auth_headers, db_session, test_user):
        """测试多页分页"""
        # 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "分页测试项目",
                "description": "描述"
            }
        )
        project_id = project_response.json()["data"]["id"]

        # 创建15个考试
        exam_ids = []
        for i in range(15):
            start_time = (utc_now() + timedelta(days=i+1)).isoformat() + "Z"
            end_time = (utc_now() + timedelta(days=i+1, hours=2)).isoformat() + "Z"

            response = client.post(
                "/api/v1/exams",
                headers=auth_headers,
                json={
                    "name": f"分页考试{i+1:02d}",
                    "description": f"描述{i+1}",
                    "start_time": start_time,
                    "end_time": end_time,
                    "project_id": project_id
                }
            )
            exam_ids.append(response.json()["data"]["id"])

        # 测试分页
        page1 = client.get("/api/v1/exams?page=1&page_size=5", headers=auth_headers)
        assert page1.json()["data"]["page"] == 1
        assert len(page1.json()["data"]["items"]) == 5

        page2 = client.get("/api/v1/exams?page=2&page_size=5", headers=auth_headers)
        assert page2.json()["data"]["page"] == 2
        assert len(page2.json()["data"]["items"]) == 5

        page3 = client.get("/api/v1/exams?page=3&page_size=5", headers=auth_headers)
        assert page3.json()["data"]["page"] == 3
        assert len(page3.json()["data"]["items"]) == 5

        # 清理
        for exam_id in exam_ids:
            client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)


class TestExamErrorHandling:
    """考试错误处理测试"""

    def test_create_exam_without_project(self, client, auth_headers):
        """测试无项目创建考试"""
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "无项目考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": "00000000-0000-0000-0000-000000000000"  # 有效格式但不存在的ID
            }
        )
        assert response.status_code == 404

    def test_update_nonexistent_exam(self, client, auth_headers):
        """测试更新不存在的考试"""
        response = client.put(
            "/api/v1/exams/non-existent-id",
            headers=auth_headers,
            json={"name": "新名称"}
        )
        assert response.status_code == 404

    def test_delete_nonexistent_exam(self, client, auth_headers):
        """测试删除不存在的考试"""
        response = client.delete(
            "/api/v1/exams/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_dismiss_nonexistent_exam(self, client, auth_headers):
        """测试关闭不存在的考试提醒"""
        response = client.post(
            "/api/v1/exams/non-existent-id/dismiss",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 404

    def test_invalid_time_format(self, client, auth_headers, db_session, test_user):
        """测试无效时间格式"""
        project = Project(name="时间格式项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "时间格式考试",
                "description": "描述",
                "start_time": "invalid-time",
                "end_time": "invalid-time",
                "project_id": project.id
            }
        )
        assert response.status_code == 422

    def test_end_time_before_start_time(self, client, auth_headers, db_session, test_user):
        """测试结束时间早于开始时间"""
        project = Project(name="时间顺序项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        start_time = (utc_now() + timedelta(days=2)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"

        response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "时间顺序考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )
        assert response.status_code == 422


class TestExamPermissionControl:
    """考试权限控制测试"""

    def test_viewer_cannot_create_exam(self, client, viewer_headers, db_session, test_user_viewer):
        """测试普通用户不能创建考试"""
        project = Project(name="权限测试项目", description="描述", owner_id=test_user_viewer.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        response = client.post(
            "/api/v1/exams",
            headers=viewer_headers,
            json={
                "name": "权限测试考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )
        assert response.status_code == 403

    def test_viewer_cannot_update_exam(self, client, auth_headers, viewer_headers, db_session, test_user):
        """测试普通用户不能更新考试"""
        project = Project(name="权限测试项目2", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 管理员创建考试
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "权限测试考试2",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )
        exam_id = create_response.json()["data"]["id"]

        # 普通用户尝试更新
        response = client.put(
            f"/api/v1/exams/{exam_id}",
            headers=viewer_headers,
            json={"name": "新名称"}
        )
        assert response.status_code == 403

        # 清理
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)

    def test_viewer_cannot_delete_exam(self, client, auth_headers, viewer_headers, db_session, test_user):
        """测试普通用户不能删除考试"""
        project = Project(name="权限测试项目3", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 管理员创建考试
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "权限测试考试3",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )
        exam_id = create_response.json()["data"]["id"]

        # 普通用户尝试删除
        response = client.delete(
            f"/api/v1/exams/{exam_id}",
            headers=viewer_headers
        )
        assert response.status_code == 403

        # 清理（使用管理员权限）
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)

    def test_any_user_can_view_exam(self, client, auth_headers, viewer_headers, db_session, test_user):
        """测试任何认证用户都可以查看考试"""
        project = Project(name="权限测试项目4", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 管理员创建考试
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "权限测试考试4",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project.id
            }
        )
        exam_id = create_response.json()["data"]["id"]

        # 普通用户可以查看
        response = client.get(
            f"/api/v1/exams/{exam_id}",
            headers=viewer_headers
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "权限测试考试4"

        # 普通用户可以获取列表
        list_response = client.get("/api/v1/exams", headers=viewer_headers)
        assert list_response.status_code == 200

        # 清理
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)


class TestExamReminderScenarios:
    """考试提醒场景测试"""

    def test_multiple_reminder_types(self, client, auth_headers, db_session, test_user):
        """测试多种提醒类型"""
        # 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "多提醒类型项目",
                "description": "描述"
            }
        )
        project_id = project_response.json()["data"]["id"]

        # 创建启用所有提醒的考试（5分钟后开始）
        start_time = (utc_now() + timedelta(minutes=5)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "多提醒类型考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_id,
                "reminder_15min": 1,
                "reminder_5min": 1,
                "reminder_start": 1
            }
        )
        exam_id = create_response.json()["data"]["id"]

        # 验证创建了3个提醒记录
        reminders = db_session.query(ExamReminder).filter(
            ExamReminder.exam_id == exam_id
        ).all()
        assert len(reminders) == 3

        reminder_types = [r.reminder_type for r in reminders]
        assert "15min" in reminder_types
        assert "5min" in reminder_types
        assert "start" in reminder_types

        # 清理
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)

    def test_partial_reminder_settings(self, client, auth_headers, db_session, test_user):
        """测试部分提醒设置"""
        # 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "部分提醒项目",
                "description": "描述"
            }
        )
        project_id = project_response.json()["data"]["id"]

        # 创建只启用15分钟提醒的考试
        start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "部分提醒考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_id,
                "reminder_15min": 1,
                "reminder_5min": 0,
                "reminder_start": 0
            }
        )
        exam_id = create_response.json()["data"]["id"]

        # 验证只创建了1个提醒记录
        reminders = db_session.query(ExamReminder).filter(
            ExamReminder.exam_id == exam_id
        ).all()
        assert len(reminders) == 1
        assert reminders[0].reminder_type == "15min"

        # 清理
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)

    def test_dismiss_specific_reminder_type_only(self, client, auth_headers, db_session, test_user):
        """测试仅关闭特定类型的提醒"""
        # 创建项目
        project_response = client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "特定关闭项目",
                "description": "描述"
            }
        )
        project_id = project_response.json()["data"]["id"]

        # 创建考试（只启用15分钟和5分钟提醒）
        start_time = (utc_now() + timedelta(minutes=10)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(hours=2)).isoformat() + "Z"

        create_response = client.post(
            "/api/v1/exams",
            headers=auth_headers,
            json={
                "name": "特定关闭考试",
                "description": "描述",
                "start_time": start_time,
                "end_time": end_time,
                "project_id": project_id,
                "reminder_15min": 1,
                "reminder_5min": 1,
                "reminder_start": 0
            }
        )
        exam_id = create_response.json()["data"]["id"]

        # 获取自动创建的提醒记录并标记为已触发
        reminders = db_session.query(ExamReminder).filter(
            ExamReminder.exam_id == exam_id
        ).all()

        reminder_15min = next((r for r in reminders if r.reminder_type == "15min"), None)
        reminder_5min = next((r for r in reminders if r.reminder_type == "5min"), None)

        # 标记为已触发
        if reminder_15min:
            reminder_15min.is_triggered = 1
        if reminder_5min:
            reminder_5min.is_triggered = 1
        db_session.commit()

        # 只关闭15分钟提醒
        dismiss_response = client.post(
            f"/api/v1/exams/{exam_id}/dismiss",
            headers=auth_headers,
            json={"reminder_type": "15min"}
        )
        assert dismiss_response.status_code == 200
        assert dismiss_response.json()["data"]["dismissed_count"] == 1

        # 验证只有15分钟提醒被关闭
        db_session.refresh(reminder_15min)
        db_session.refresh(reminder_5min)
        assert reminder_15min.is_dismissed == 1
        assert reminder_5min.is_dismissed == 0

        # 清理
        client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)
