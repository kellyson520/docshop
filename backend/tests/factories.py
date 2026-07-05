"""
测试数据工厂。

用于生成测试时需要的模拟数据字典，避免依赖真实 ORM 实例。
"""

from datetime import timedelta
import random

import factory
from factory import Faker, LazyAttribute, Sequence
from factory.fuzzy import FuzzyChoice, FuzzyInteger

from app.utils.time import utc_now


class UserFactory(factory.Factory):
    class Meta:
        model = dict

    id = Sequence(lambda n: n + 1)
    username = Sequence(lambda n: f"user{n}")
    email = LazyAttribute(lambda obj: f"{obj['username']}@example.com")
    password_hash = "hashed_password"
    is_admin = False
    created_at = factory.LazyFunction(utc_now)
    updated_at = factory.LazyFunction(utc_now)


class AdminUserFactory(UserFactory):
    username = Sequence(lambda n: f"admin{n}")
    is_admin = True


class ProjectFactory(factory.Factory):
    class Meta:
        model = dict

    id = Sequence(lambda n: n + 1)
    name = Sequence(lambda n: f"测试项目{n}")
    description = Faker("text", max_nb_chars=200)
    owner_id = Sequence(lambda n: n + 1)
    is_public = FuzzyChoice([True, False])
    share_token = LazyAttribute(lambda obj: f"token_{obj['id']}" if obj["is_public"] else None)
    created_at = factory.LazyFunction(utc_now)
    updated_at = factory.LazyFunction(utc_now)


class FileFactory(factory.Factory):
    class Meta:
        model = dict

    id = Sequence(lambda n: n + 1)
    name = FuzzyChoice(["document.pdf", "report.docx", "data.xlsx", "image.png"])
    original_name = LazyAttribute(lambda obj: obj["name"])
    path = LazyAttribute(lambda obj: f"/uploads/{obj['id']}/{obj['name']}")
    size = FuzzyInteger(1024, 50 * 1024 * 1024)
    mime_type = LazyAttribute(lambda obj: {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png": "image/png",
    }.get(f".{obj['name'].split('.')[-1]}", "application/octet-stream"))
    project_id = Sequence(lambda n: n + 1)
    current_version = 1
    created_at = factory.LazyFunction(utc_now)
    updated_at = factory.LazyFunction(utc_now)


class FileVersionFactory(factory.Factory):
    class Meta:
        model = dict

    id = Sequence(lambda n: n + 1)
    file_id = Sequence(lambda n: n + 1)
    version = Sequence(lambda n: n + 1)
    path = LazyAttribute(lambda obj: f"/uploads/{obj['file_id']}/v{obj['version']}/file")
    size = FuzzyInteger(1024, 50 * 1024 * 1024)
    changelog = Faker("sentence")
    created_by = Sequence(lambda n: n + 1)
    created_at = factory.LazyFunction(utc_now)


class ExamFactory(factory.Factory):
    class Meta:
        model = dict

    id = Sequence(lambda n: n + 1)
    name = Sequence(lambda n: f"考试{n}")
    description = Faker("text", max_nb_chars=100)
    project_id = Sequence(lambda n: n + 1)
    start_time = factory.LazyFunction(lambda: utc_now() + timedelta(days=random.randint(1, 30)))
    end_time = LazyAttribute(lambda obj: obj["start_time"] + timedelta(hours=random.randint(1, 4)))
    created_by = Sequence(lambda n: n + 1)
    created_at = factory.LazyFunction(utc_now)
    updated_at = factory.LazyFunction(utc_now)


class ExamReminderFactory(factory.Factory):
    class Meta:
        model = dict

    id = Sequence(lambda n: n + 1)
    exam_id = Sequence(lambda n: n + 1)
    user_id = Sequence(lambda n: n + 1)
    reminder_type = FuzzyChoice(["email", "popup", "sms"])
    minutes_before = FuzzyChoice([15, 30, 60, 120, 1440])
    is_triggered = False
    is_dismissed = False
    triggered_at = None
    created_at = factory.LazyFunction(utc_now)


def create_batch(factory_class, size=10, **kwargs):
    return [factory_class(**kwargs) for _ in range(size)]


def create_user_batch(size=5, is_admin=False):
    factory_class = AdminUserFactory if is_admin else UserFactory
    return create_batch(factory_class, size)


def create_project_batch(user_id, size=5):
    return create_batch(ProjectFactory, size, owner_id=user_id)


def create_file_batch(project_id, size=10):
    return create_batch(FileFactory, size, project_id=project_id)


def create_exam_batch(project_id, user_id, size=5):
    return create_batch(ExamFactory, size, project_id=project_id, created_by=user_id)


class TestDataGenerator:
    @staticmethod
    def generate_large_file_list(count=1000):
        return create_batch(FileFactory, count)

    @staticmethod
    def generate_large_project_list(count=500):
        return create_batch(ProjectFactory, count)

    @staticmethod
    def generate_exam_schedule(project_id, user_id, days=30):
        exams = []
        base_date = utc_now()
        for day in range(days):
            if random.random() < 0.3:
                exam_date = base_date + timedelta(days=day)
                exams.append(ExamFactory(
                    project_id=project_id,
                    created_by=user_id,
                    start_time=exam_date.replace(hour=9, minute=0, second=0, microsecond=0),
                    end_time=exam_date.replace(hour=12, minute=0, second=0, microsecond=0),
                ))
        return exams

    @staticmethod
    def generate_mixed_file_types(project_id, count=50):
        extensions = [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".jpg", ".png"]
        files = []
        for i in range(count):
            ext = random.choice(extensions)
            files.append(FileFactory(
                project_id=project_id,
                name=f"file_{i}{ext}",
                original_name=f"file_{i}{ext}",
            ))
        return files
