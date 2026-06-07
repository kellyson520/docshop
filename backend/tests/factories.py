/**
 * 测试数据工厂
 * 用于生成测试用的模拟数据
 */

import factory
from factory import Faker, Sequence, LazyAttribute
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyDateTime
from datetime import datetime, timedelta
import random

# 用户工厂
class UserFactory(factory.Factory):
    class Meta:
        model = dict  # 使用 dict 代替实际模型
    
    id = Sequence(lambda n: n)
    username = Sequence(lambda n: f"user{n}")
    email = LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password_hash = "hashed_password"
    is_admin = False
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)

# 管理员用户工厂
class AdminUserFactory(UserFactory):
    username = Sequence(lambda n: f"admin{n}")
    is_admin = True

# 项目工厂
class ProjectFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = Sequence(lambda n: n)
    name = Sequence(lambda n: f"测试项目{n}")
    description = Faker('text', max_nb_chars=200)
    owner_id = factory.SubFactory(UserFactory)
    is_public = FuzzyChoice([True, False])
    share_token = LazyAttribute(lambda obj: f"token_{obj.id}" if obj.is_public else None)
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)

# 文件工厂
class FileFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = Sequence(lambda n: n)
    name = FuzzyChoice(['document.pdf', 'report.docx', 'data.xlsx', 'image.png'])
    original_name = LazyAttribute(lambda obj: obj.name)
    path = LazyAttribute(lambda obj: f"/uploads/{obj.id}/{obj.name}")
    size = FuzzyInteger(1024, 50*1024*1024)  # 1KB to 50MB
    mime_type = LazyAttribute(lambda obj: {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.png': 'image/png'
    }.get(f".{obj.name.split('.')[-1]}", 'application/octet-stream'))
    project_id = factory.SubFactory(ProjectFactory)
    current_version = 1
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)

# 文件版本工厂
class FileVersionFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = Sequence(lambda n: n)
    file_id = factory.SubFactory(FileFactory)
    version = Sequence(lambda n: n)
    path = LazyAttribute(lambda obj: f"/uploads/{obj.file_id}/v{obj.version}/file")
    size = FuzzyInteger(1024, 50*1024*1024)
    changelog = Faker('sentence')
    created_by = factory.SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.now)

# 考试工厂
class ExamFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = Sequence(lambda n: n)
    name = Sequence(lambda n: f"考试{n}")
    description = Faker('text', max_nb_chars=100)
    project_id = factory.SubFactory(ProjectFactory)
    start_time = factory.LazyFunction(lambda: datetime.now() + timedelta(days=random.randint(1, 30)))
    end_time = LazyAttribute(lambda obj: obj.start_time + timedelta(hours=random.randint(1, 4)))
    created_by = factory.SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)

# 考试提醒工厂
class ExamReminderFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = Sequence(lambda n: n)
    exam_id = factory.SubFactory(ExamFactory)
    user_id = factory.SubFactory(UserFactory)
    reminder_type = FuzzyChoice(['email', 'popup', 'sms'])
    minutes_before = FuzzyChoice([15, 30, 60, 120, 1440])
    is_triggered = False
    is_dismissed = False
    triggered_at = None
    created_at = factory.LazyFunction(datetime.now)

# 批量创建辅助函数
def create_batch(factory_class, size=10, **kwargs):
    """批量创建测试数据"""
    return [factory_class(**kwargs) for _ in range(size)]

def create_user_batch(size=5, is_admin=False):
    """批量创建用户"""
    factory = AdminUserFactory if is_admin else UserFactory
    return create_batch(factory, size)

def create_project_batch(user_id, size=5):
    """批量创建项目"""
    return create_batch(ProjectFactory, size, owner_id=user_id)

def create_file_batch(project_id, size=10):
    """批量创建文件"""
    return create_batch(FileFactory, size, project_id=project_id)

def create_exam_batch(project_id, user_id, size=5):
    """批量创建考试"""
    return create_batch(ExamFactory, size, project_id=project_id, created_by=user_id)

# 测试数据生成器
class TestDataGenerator:
    """测试数据生成器，用于生成各种测试场景所需的数据"""
    
    @staticmethod
    def generate_large_file_list(count=1000):
        """生成大量文件数据用于性能测试"""
        return create_batch(FileFactory, count)
    
    @staticmethod
    def generate_large_project_list(count=500):
        """生成大量项目数据用于性能测试"""
        return create_batch(ProjectFactory, count)
    
    @staticmethod
    def generate_exam_schedule(project_id, user_id, days=30):
        """生成一个月内的考试安排"""
        exams = []
        base_date = datetime.now()
        for day in range(days):
            if random.random() < 0.3:  # 30% 概率每天有考试
                exam_date = base_date + timedelta(days=day)
                exams.append(ExamFactory(
                    project_id=project_id,
                    created_by=user_id,
                    start_time=exam_date.replace(hour=9, minute=0),
                    end_time=exam_date.replace(hour=12, minute=0)
                ))
        return exams
    
    @staticmethod
    def generate_mixed_file_types(project_id, count=50):
        """生成混合类型的文件"""
        extensions = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.jpg', '.png']
        files = []
        for i in range(count):
            ext = random.choice(extensions)
            files.append(FileFactory(
                project_id=project_id,
                name=f"file_{i}{ext}",
                original_name=f"file_{i}{ext}"
            ))
        return files
