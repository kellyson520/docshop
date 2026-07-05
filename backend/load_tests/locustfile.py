"""
DocShop 负载测试脚本。

运行示例：
    locust -f backend/load_tests/locustfile.py --host=http://localhost:8000

覆盖场景：登录鉴权、项目列表/搜索、项目创建/删除、文件上传、版本查询、高频请求。
"""

from __future__ import annotations

import random
import time
from locust import HttpUser, between, events, task
from locust.runners import MasterRunner


class DocShopUser(HttpUser):
    """模拟普通 DocShop 用户行为。"""

    wait_time = between(1, 5)

    def on_start(self) -> None:
        self.username = f"loadtest_{id(self)}_{int(time.time())}"
        self.password = "TestPass123!"
        self.token = None
        self.project_id = None
        self.file_id = None
        self._register()
        self._login()
        self._create_project()

    def _register(self) -> None:
        response = self.client.post("/api/v1/auth/register", json={"username": self.username, "password": self.password})
        if response.status_code in (200, 201):
            print(f"用户 {self.username} 注册成功")
        elif "已存在" in response.text:
            print(f"用户 {self.username} 已存在，继续登录")
        else:
            print(f"注册失败: {response.status_code} {response.text}")

    def _login(self) -> None:
        response = self.client.post("/api/v1/auth/login", json={"username": self.username, "password": self.password})
        if response.status_code != 200:
            print(f"登录失败: {response.status_code} {response.text}")
            return
        self.token = response.json().get("data", {}).get("access_token")
        if self.token:
            print(f"用户 {self.username} 登录成功")

    def _get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _create_project(self) -> None:
        if not self.token:
            return
        response = self.client.post(
            "/api/v1/projects",
            json={"name": f"LoadTestProject_{int(time.time())}"},
            headers=self._get_headers(),
        )
        if response.status_code in (200, 201):
            self.project_id = response.json().get("data", {}).get("id")
            print(f"项目 {self.project_id} 创建成功")

    @task(5)
    def get_projects_list(self) -> None:
        """测试项目分页列表。"""
        if not self.token:
            return
        page = random.randint(1, 5)
        page_size = random.choice([10, 20, 50])
        with self.client.get(
            f"/api/v1/projects?page={page}&page_size={page_size}",
            headers=self._get_headers(),
            catch_response=True,
            name="GET /api/v1/projects (list)",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取项目列表失败: {response.status_code}")

    @task(3)
    def search_projects(self) -> None:
        """测试项目搜索。"""
        if not self.token:
            return
        keyword = random.choice(["test", "project", "load", "doc", "pdf"])
        with self.client.get(
            f"/api/v1/projects?keyword={keyword}",
            headers=self._get_headers(),
            catch_response=True,
            name="GET /api/v1/projects (search)",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"搜索项目失败: {response.status_code}")

    @task(2)
    def create_and_delete_project(self) -> None:
        """测试项目创建和删除。"""
        if not self.token:
            return
        project_name = f"TempProject_{int(time.time())}_{random.randint(1000, 9999)}"
        with self.client.post(
            "/api/v1/projects",
            json={"name": project_name},
            headers=self._get_headers(),
            catch_response=True,
            name="POST /api/v1/projects (create)",
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"创建项目失败: {response.status_code}")
                return
            project_id = response.json().get("data", {}).get("id")
            response.success()
            if project_id:
                self.client.delete(f"/api/v1/projects/{project_id}", headers=self._get_headers(), name="DELETE /api/v1/projects/{id}")

    @task(4)
    def upload_small_file(self) -> None:
        """测试 100KB 小文件上传。"""
        if not self.token or not self.project_id:
            return
        file_content = b"%PDF-1.4\n" + b"x" * (100 * 1024)
        filename = f"small_test_{int(time.time())}.pdf"
        with self.client.post(
            f"/api/v1/projects/{self.project_id}/files",
            files={"file": (filename, file_content, "application/pdf")},
            headers=self._get_headers(),
            catch_response=True,
            name="POST /api/v1/projects/{id}/files (small upload)",
        ) as response:
            if response.status_code in (200, 201):
                self.file_id = response.json().get("data", {}).get("id")
                response.success()
            else:
                response.failure(f"上传小文件失败: {response.status_code}")

    @task(1)
    def upload_medium_file(self) -> None:
        """测试 1MB 文件上传。"""
        if not self.token or not self.project_id:
            return
        file_content = b"%PDF-1.4\n" + b"x" * (1024 * 1024)
        filename = f"medium_test_{int(time.time())}.pdf"
        start_time = time.time()
        with self.client.post(
            f"/api/v1/projects/{self.project_id}/files",
            files={"file": (filename, file_content, "application/pdf")},
            headers=self._get_headers(),
            catch_response=True,
            name="POST /api/v1/projects/{id}/files (medium upload)",
        ) as response:
            elapsed = time.time() - start_time
            if response.status_code not in (200, 201):
                response.failure(f"上传 1MB 文件失败: {response.status_code}")
            elif elapsed > 5.0:
                response.failure(f"上传 1MB 文件过慢: {elapsed:.2f}s")
            else:
                response.success()

    @task(3)
    def get_file_versions(self) -> None:
        """测试文件版本查询。"""
        if not self.token or not self.file_id:
            return
        with self.client.get(
            f"/api/v1/files/{self.file_id}/versions",
            headers=self._get_headers(),
            catch_response=True,
            name="GET /api/v1/files/{id}/versions",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取文件版本失败: {response.status_code}")

    @task(2)
    def get_user_info(self) -> None:
        """测试当前用户信息接口。"""
        if not self.token:
            return
        with self.client.get("/api/v1/auth/me", headers=self._get_headers(), catch_response=True, name="GET /api/v1/auth/me") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取用户信息失败: {response.status_code}")


class HighLoadUser(HttpUser):
    """模拟高频请求用户。"""

    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        self.username = f"highload_{int(time.time())}_{random.randint(1000, 9999)}"
        self.password = "TestPass123!"
        self.token = None
        self.client.post("/api/v1/auth/register", json={"username": self.username, "password": self.password})
        response = self.client.post("/api/v1/auth/login", json={"username": self.username, "password": self.password})
        if response.status_code == 200:
            self.token = response.json().get("data", {}).get("access_token")

    def _get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(10)
    def rapid_api_calls(self) -> None:
        """测试快速连续 API 调用。"""
        if not self.token:
            return
        with self.client.get("/api/v1/projects", headers=self._get_headers(), catch_response=True, name="RAPID GET /api/v1/projects") as response:
            if response.status_code in (200, 429):
                response.success()
            else:
                response.failure(f"快速请求失败: {response.status_code}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """记录慢请求。"""
    if response_time > 2000:
        print(f"[慢请求] {name}: {response_time:.0f}ms")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """测试结束时输出摘要。"""
    if not isinstance(environment.runner, MasterRunner):
        return
    print("\n" + "=" * 60)
    print("DocShop 负载测试摘要")
    print("=" * 60)
    for name, entry in environment.runner.stats.entries.items():
        print(f"\n{name}:")
        print(f"  请求数: {entry.num_requests}")
        print(f"  失败数: {entry.num_failures}")
        print(f"  平均响应时间: {entry.avg_response_time:.2f}ms")
        print(f"  最大响应时间: {entry.max_response_time:.2f}ms")
        print(f"  RPS: {entry.total_rps:.2f}")


@events.init_command_line_parser.add_listener
def on_init_command_line_parser(parser):
    parser.add_argument("--test-duration", type=int, default=300, help="测试持续时间（秒）")
    parser.add_argument("--target-rps", type=int, default=100, help="目标 RPS")
