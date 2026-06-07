"""
负载测试 - 使用 Locust 进行压力测试

测试场景：
1. API响应时间测试
2. 并发请求处理
3. 大文件上传下载
4. 数据库查询性能

运行方式：
    locust -f tests/performance/test_load.py --host=http://localhost:8000
"""

import random
import string
import time
from typing import Optional

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


class DocDistUser(HttpUser):
    """模拟 DocDist 用户行为的负载测试用户"""
    
    wait_time = between(1, 5)  # 请求间隔 1-5 秒
    
    def on_start(self):
        """用户启动时执行：注册并登录"""
        self.username = f"loadtest_{self.user_id}_{int(time.time())}"
        self.password = "TestPass123!"
        self.token = None
        self.project_id = None
        self.file_id = None
        
        # 注册用户
        self._register()
        # 登录获取 token
        self._login()
        # 创建测试项目
        self._create_project()
    
    def _register(self):
        """注册用户"""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": self.username,
                "password": self.password
            }
        )
        if response.status_code == 201 or response.status_code == 200:
            print(f"用户 {self.username} 注册成功")
        elif "已存在" in response.text:
            print(f"用户 {self.username} 已存在，继续登录")
        else:
            print(f"注册失败: {response.text}")
    
    def _login(self):
        """用户登录"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "username": self.username,
                "password": self.password
            }
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                self.token = data["data"].get("access_token")
                print(f"用户 {self.username} 登录成功")
        else:
            print(f"登录失败: {response.text}")
    
    def _get_headers(self):
        """获取认证请求头"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def _create_project(self):
        """创建测试项目"""
        if not self.token:
            return
        
        response = self.client.post(
            "/api/v1/projects",
            json={"name": f"LoadTestProject_{int(time.time())}"},
            headers=self._get_headers()
        )
        if response.status_code == 201:
            data = response.json()
            if data.get("data"):
                self.project_id = data["data"].get("id")
                print(f"项目 {self.project_id} 创建成功")
    
    @task(5)
    def get_projects_list(self):
        """测试项目列表查询性能"""
        if not self.token:
            return
        
        # 随机分页参数
        page = random.randint(1, 5)
        page_size = random.choice([10, 20, 50])
        
        with self.client.get(
            f"/api/v1/projects?page={page}&page_size={page_size}",
            headers=self._get_headers(),
            catch_response=True,
            name="GET /api/v1/projects (list)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取项目列表失败: {response.status_code}")
    
    @task(3)
    def search_projects(self):
        """测试项目搜索性能"""
        if not self.token:
            return
        
        # 随机搜索关键词
        keywords = ["test", "project", "load", "doc", "pdf"]
        keyword = random.choice(keywords)
        
        with self.client.get(
            f"/api/v1/projects?keyword={keyword}",
            headers=self._get_headers(),
            catch_response=True,
            name="GET /api/v1/projects (search)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"搜索项目失败: {response.status_code}")
    
    @task(2)
    def create_and_delete_project(self):
        """测试项目创建和删除性能"""
        if not self.token:
            return
        
        # 创建项目
        project_name = f"TempProject_{int(time.time())}_{random.randint(1000, 9999)}"
        
        with self.client.post(
            "/api/v1/projects",
            json={"name": project_name},
            headers=self._get_headers(),
            catch_response=True,
            name="POST /api/v1/projects (create)"
        ) as response:
            if response.status_code == 201:
                data = response.json()
                project_id = data.get("data", {}).get("id")
                response.success()
                
                # 立即删除创建的项目
                if project_id:
                    self.client.delete(
                        f"/api/v1/projects/{project_id}",
                        headers=self._get_headers(),
                        name="DELETE /api/v1/projects/{id}"
                    )
            else:
                response.failure(f"创建项目失败: {response.status_code}")
    
    @task(4)
    def upload_small_file(self):
        """测试小文件上传性能（100KB）"""
        if not self.token or not self.project_id:
            return
        
        # 生成 100KB 的测试文件内容
        file_content = b"%PDF-1.4\n" + b"x" * (100 * 1024)
        filename = f"small_test_{int(time.time())}.pdf"
        
        with self.client.post(
            f"/api/v1/projects/{self.project_id}/files",
            files={"file": (filename, file_content, "application/pdf")},
            headers=self._get_headers(),
            catch_response=True,
            name="POST /api/v1/projects/{id}/files (small upload)"
        ) as response:
            if response.status_code == 201:
                data = response.json()
                file_id = data.get("data", {}).get("id")
                response.success()
                # 保存文件ID用于后续下载测试
                if file_id:
                    self.file_id = file_id
            else:
                response.failure(f"上传小文件失败: {response.status_code}")
    
    @task(1)
    def upload_medium_file(self):
        """测试中等文件上传性能（1MB）"""
        if not self.token or not self.project_id:
            return
        
        # 生成 1MB 的测试文件内容
        file_content = b"%PDF-1.4\n" + b"x" * (1024 * 1024)
        filename = f"medium_test_{int(time.time())}.pdf"
        
        start_time = time.time()
        with self.client.post(
            f"/api/v1/projects/{self.project_id}/files",
            files={"file": (filename, file_content, "application/pdf")},
            headers=self._get_headers(),
            catch_response=True,
            name="POST /api/v1/projects/{id}/files (medium upload)"
        ) as response:
            elapsed = time.time() - start_time
            if response.status_code == 201:
                # 1MB 文件上传应该在 5 秒内完成
                if elapsed < 5.0:
                    response.success()
                else:
                    response.failure(f"1MB文件上传太慢: {elapsed:.2f}s")
            else:
                response.failure(f"上传中等文件失败: {response.status_code}")
    
    @task(3)
    def download_file(self):
        """测试文件下载性能"""
        if not self.token or not self.file_id:
            return
        
        # 先上传一个小文件用于下载测试
        file_content = b"%PDF-1.4\n" + b"x" * (50 * 1024)
        filename = f"dl_test_{int(time.time())}.pdf"
        
        upload_resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/files",
            files={"file": (filename, file_content, "application/pdf")},
            headers=self._get_headers()
        )
        
        if upload_resp.status_code == 201:
            file_id = upload_resp.json().get("data", {}).get("id")
            
            with self.client.get(
                f"/api/v1/files/{file_id}/versions",
                headers=self._get_headers(),
                catch_response=True,
                name="GET /api/v1/files/{id}/versions"
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"获取文件版本失败: {response.status_code}")
    
    @task(2)
    def get_user_info(self):
        """测试用户信息查询性能"""
        if not self.token:
            return
        
        with self.client.get(
            "/api/v1/auth/me",
            headers=self._get_headers(),
            catch_response=True,
            name="GET /api/v1/auth/me"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"获取用户信息失败: {response.status_code}")


class HighLoadUser(HttpUser):
    """高负载测试用户 - 更频繁的请求"""
    
    wait_time = between(0.1, 0.5)  # 更短的请求间隔
    
    def on_start(self):
        """快速注册登录"""
        self.username = f"highload_{int(time.time())}_{random.randint(1000, 9999)}"
        self.password = "TestPass123!"
        self.token = None
        
        # 注册并登录
        self.client.post(
            "/api/v1/auth/register",
            json={"username": self.username, "password": self.password}
        )
        
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": self.username, "password": self.password}
        )
        if response.status_code == 200:
            self.token = response.json().get("data", {}).get("access_token")
    
    def _get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    @task(10)
    def rapid_api_calls(self):
        """快速API调用测试"""
        if not self.token:
            return
        
        # 快速连续请求
        with self.client.get(
            "/api/v1/projects",
            headers=self._get_headers(),
            catch_response=True,
            name="RAPID GET /api/v1/projects"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:  # 限流
                response.success()  # 限流是预期行为
            else:
                response.failure(f"快速请求失败: {response.status_code}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, 
               context, exception, start_time, url, **kwargs):
    """请求事件监听器 - 记录性能指标"""
    # 记录慢请求
    if response_time > 2000:  # 超过2秒的请求
        print(f"[慢请求警告] {name}: {response_time:.0f}ms")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """测试结束时输出统计信息"""
    if isinstance(environment.runner, MasterRunner):
        print("\n" + "="*60)
        print("负载测试完成 - 统计摘要")
        print("="*60)
        stats = environment.runner.stats
        
        # 输出关键指标
        for name in stats.entries.keys():
            entry = stats.entries[name]
            print(f"\n{name}:")
            print(f"  请求数: {entry.num_requests}")
            print(f"  失败数: {entry.num_failures}")
            print(f"  平均响应时间: {entry.avg_response_time:.2f}ms")
            print(f"  最大响应时间: {entry.max_response_time:.2f}ms")
            print(f"  RPS: {entry.total_rps:.2f}")


# 自定义命令行参数
@events.init_command_line_parser.add_listener
def on_init_command_line_parser(parser):
    parser.add_argument(
        "--test-duration",
        type=int,
        default=300,
        help="测试持续时间（秒）"
    )
    parser.add_argument(
        "--target-rps",
        type=int,
        default=100,
        help="目标RPS"
    )
