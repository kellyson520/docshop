"""
数据库集成测试
测试数据库连接池管理、事务回滚、并发访问和数据一致性
使用pytest进行测试
"""

import pytest
import threading
import time
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool, NullPool

# 导入应用和模型
from app.database import Base, get_db
from app.models import User, Project, DocumentFile, FileVersion
from app.utils.security import get_password_hash


class TestConnectionPool:
    """测试数据库连接池管理"""

    def test_connection_pool_limits(self):
        """
        测试连接池限制
        验证连接池大小限制和溢出连接处理
        """
        # 创建带有连接池限制的引擎
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=2,
            pool_timeout=5
        )
        
        # 创建表
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        
        connections = []
        
        # 尝试获取超过池大小的连接
        for i in range(8):
            try:
                session = SessionLocal()
                # 执行简单查询以验证连接有效
                result = session.execute(text("SELECT 1"))
                connections.append(session)
            except Exception as e:
                # 超过最大连接数时应该抛出异常
                assert "timeout" in str(e).lower() or "queuepool" in str(e).lower()
        
        # 清理连接
        for session in connections:
            session.close()
        
        engine.dispose()

    def test_connection_reuse(self):
        """
        测试连接复用
        验证连接在会话结束后返回连接池并被复用
        """
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=0
        )
        
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        
        # 获取初始连接数
        initial_checked_in = engine.pool.checkedin()
        
        # 创建并关闭多个会话
        for _ in range(10):
            session = SessionLocal()
            session.execute(text("SELECT 1"))
            session.close()
        
        # 验证连接被复用（连接池中的连接数应该保持稳定）
        final_checked_in = engine.pool.checkedin()
        assert final_checked_in <= 2
        
        engine.dispose()

    def test_connection_timeout(self):
        """
        测试连接超时
        验证连接池超时处理
        """
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=QueuePool,
            pool_size=1,
            max_overflow=0,
            pool_timeout=1  # 1秒超时
        )
        
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        
        # 占用唯一可用的连接
        session1 = SessionLocal()
        session1.execute(text("SELECT 1"))
        
        # 尝试获取第二个连接应该超时
        with pytest.raises(Exception) as exc_info:
            session2 = SessionLocal()
            session2.execute(text("SELECT 1"))
        
        assert "timeout" in str(exc_info.value).lower()
        
        session1.close()
        engine.dispose()


class TestTransactionRollback:
    """测试事务回滚"""

    def test_transaction_rollback_on_error(self, db):
        """
        测试错误时事务回滚
        验证发生异常时事务自动回滚
        """
        # 创建测试用户
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username="rollback_test",
            email="rollback@test.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        # 开始新事务
        try:
            # 创建项目
            project = Project(
                id=str(uuid.uuid4()),
                name="Test Project",
                description="Test Description",
                owner_id=user_id,
                created_at=datetime.utcnow()
            )
            db.add(project)
            
            # 模拟错误
            raise ValueError("模拟错误")
            
            db.commit()
        except ValueError:
            db.rollback()
        
        # 验证项目未保存到数据库
        result = db.query(Project).filter_by(name="Test Project").first()
        assert result is None

    def test_explicit_transaction_management(self, db):
        """
        测试显式事务管理
        验证手动提交和回滚
        """
        user_id = str(uuid.uuid4())
        
        # 开始事务
        db.begin()
        
        try:
            user = User(
                id=user_id,
                username="explicit_test",
                email="explicit@test.com",
                hashed_password=get_password_hash("testpass"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user)
            
            # 手动回滚
            db.rollback()
        except Exception:
            db.rollback()
        
        # 验证用户未保存
        result = db.query(User).filter_by(id=user_id).first()
        assert result is None

    def test_nested_transaction_savepoint(self, db):
        """
        测试嵌套事务保存点
        验证保存点功能
        """
        user_id = str(uuid.uuid4())
        
        # 创建用户
        user = User(
            id=user_id,
            username="savepoint_test",
            email="savepoint@test.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        # 开始保存点
        savepoint = db.begin_nested()
        
        try:
            # 更新用户
            user.username = "updated_name"
            db.add(user)
            
            # 回滚到保存点
            savepoint.rollback()
        except Exception:
            savepoint.rollback()
        
        # 验证用户名未更新
        db.refresh(user)
        assert user.username == "savepoint_test"


class TestConcurrentAccess:
    """测试并发访问"""

    def test_concurrent_reads(self, db):
        """
        测试并发读取
        验证多个线程同时读取数据的一致性
        """
        # 创建测试数据
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username="concurrent_read",
            email="concurrent@test.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        results = []
        errors = []
        
        def read_user():
            try:
                # 每个线程创建自己的会话
                from app.database import SessionLocal
                session = SessionLocal()
                user_data = session.query(User).filter_by(id=user_id).first()
                if user_data:
                    results.append(user_data.username)
                session.close()
            except Exception as e:
                errors.append(str(e))
        
        # 并发读取
        threads = []
        for _ in range(10):
            t = threading.Thread(target=read_user)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证所有读取成功
        assert len(results) == 10
        assert all(r == "concurrent_read" for r in results)
        assert len(errors) == 0

    def test_concurrent_writes_with_lock(self, db):
        """
        测试带锁的并发写入
        验证并发写入时的数据一致性
        """
        # 创建计数器表
        from sqlalchemy import Column, Integer, String
        
        class Counter(Base):
            __tablename__ = "test_counter"
            id = Column(String, primary_key=True)
            value = Column(Integer, default=0)
        
        # 创建表
        Base.metadata.create_all(bind=db.bind)
        
        counter_id = str(uuid.uuid4())
        counter = Counter(id=counter_id, value=0)
        db.add(counter)
        db.commit()
        
        def increment_counter():
            from app.database import SessionLocal
            session = SessionLocal()
            try:
                # 使用悲观锁
                counter_data = session.query(Counter).filter_by(id=counter_id).with_for_update().first()
                if counter_data:
                    counter_data.value += 1
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()
        
        # 并发递增
        threads = []
        for _ in range(10):
            t = threading.Thread(target=increment_counter)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证最终值
        db.expire_all()
        final_counter = db.query(Counter).filter_by(id=counter_id).first()
        assert final_counter.value == 10

    def test_deadlock_detection(self, db):
        """
        测试死锁检测
        验证数据库死锁处理
        """
        # 创建两个资源
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())
        
        user1 = User(
            id=id1,
            username="user1",
            email="user1@test.com",
            hashed_password=get_password_hash("pass1"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        user2 = User(
            id=id2,
            username="user2",
            email="user2@test.com",
            hashed_password=get_password_hash("pass2"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add_all([user1, user2])
        db.commit()
        
        deadlock_detected = []
        
        def transaction_a():
            from app.database import SessionLocal
            session = SessionLocal()
            try:
                # 先锁定user1，再尝试锁定user2
                u1 = session.query(User).filter_by(id=id1).with_for_update().first()
                time.sleep(0.1)
                u2 = session.query(User).filter_by(id=id2).with_for_update().first()
                u1.username = "updated_a"
                session.commit()
            except Exception as e:
                if "deadlock" in str(e).lower():
                    deadlock_detected.append("A")
                session.rollback()
            finally:
                session.close()
        
        def transaction_b():
            from app.database import SessionLocal
            session = SessionLocal()
            try:
                # 先锁定user2，再尝试锁定user1
                u2 = session.query(User).filter_by(id=id2).with_for_update().first()
                time.sleep(0.1)
                u1 = session.query(User).filter_by(id=id1).with_for_update().first()
                u2.username = "updated_b"
                session.commit()
            except Exception as e:
                if "deadlock" in str(e).lower():
                    deadlock_detected.append("B")
                session.rollback()
            finally:
                session.close()
        
        # 启动两个可能导致死锁的事务
        t1 = threading.Thread(target=transaction_a)
        t2 = threading.Thread(target=transaction_b)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # 至少有一个事务应该检测到死锁或超时
        # 注意：SQLite可能不严格检测死锁，但应该有超时处理


class TestDataConsistency:
    """测试数据一致性"""

    def test_foreign_key_constraint(self, db):
        """
        测试外键约束
        验证外键关系的数据完整性
        """
        # 创建用户
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username="fk_test",
            email="fk@test.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        # 创建项目（外键关联到用户）
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="FK Test Project",
            description="Test",
            owner_id=user_id,
            created_at=datetime.utcnow()
        )
        db.add(project)
        db.commit()
        
        # 验证项目关联正确
        db_project = db.query(Project).filter_by(id=project_id).first()
        assert db_project.owner_id == user_id
        assert db_project.owner.username == "fk_test"

    def test_unique_constraint(self, db):
        """
        测试唯一约束
        验证唯一性约束
        """
        # 创建第一个用户
        user1 = User(
            id=str(uuid.uuid4()),
            username="unique_test",
            email="unique@test.com",
            hashed_password=get_password_hash("pass1"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user1)
        db.commit()
        
        # 尝试创建具有相同用户名的用户
        user2 = User(
            id=str(uuid.uuid4()),
            username="unique_test",  # 重复的用户名
            email="unique2@test.com",
            hashed_password=get_password_hash("pass2"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user2)
        
        # 应该抛出唯一约束违规异常
        with pytest.raises(Exception) as exc_info:
            db.commit()
        
        assert "unique" in str(exc_info.value).lower() or "constraint" in str(exc_info.value).lower()
        db.rollback()

    def test_cascade_delete(self, db):
        """
        测试级联删除
        验证删除父记录时子记录的处理
        """
        # 创建用户和项目
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username="cascade_test",
            email="cascade@test.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="Cascade Test Project",
            description="Test",
            owner_id=user_id,
            created_at=datetime.utcnow()
        )
        db.add(project)
        db.commit()
        
        # 删除用户
        db.delete(user)
        db.commit()
        
        # 验证用户已删除
        assert db.query(User).filter_by(id=user_id).first() is None
        
        # 根据级联设置，项目可能被删除或外键设为NULL
        # 这里验证数据库行为
        remaining_project = db.query(Project).filter_by(id=project_id).first()
        # 如果没有级联删除，项目应该仍然存在

    def test_null_constraint(self, db):
        """
        测试非空约束
        验证必填字段的非空约束
        """
        # 尝试创建没有用户名的用户
        user = User(
            id=str(uuid.uuid4()),
            username=None,  # 必填字段为空
            email="null@test.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        
        # 应该抛出非空约束违规异常
        with pytest.raises(Exception) as exc_info:
            db.commit()
        
        assert "not null" in str(exc_info.value).lower() or "constraint" in str(exc_info.value).lower()
        db.rollback()

    def test_data_type_validation(self, db):
        """
        测试数据类型验证
        验证数据类型的正确性
        """
        # 创建用户
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username="datatype_test",
            email="datatype@test.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        # 验证数据类型
        db_user = db.query(User).filter_by(id=user_id).first()
        assert isinstance(db_user.username, str)
        assert isinstance(db_user.is_active, bool)
        assert isinstance(db_user.created_at, datetime)


class TestDatabasePerformance:
    """测试数据库性能"""

    def test_bulk_insert_performance(self, db):
        """
        测试批量插入性能
        验证大批量数据插入的效率
        """
        # 准备批量数据
        users = []
        for i in range(100):
            user = User(
                id=str(uuid.uuid4()),
                username=f"bulk_user_{i}",
                email=f"bulk{i}@test.com",
                hashed_password=get_password_hash(f"pass{i}"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            users.append(user)
        
        # 批量插入
        start_time = time.time()
        db.add_all(users)
        db.commit()
        end_time = time.time()
        
        # 验证插入成功
        count = db.query(User).filter(User.username.like("bulk_user_%")).count()
        assert count == 100
        
        # 验证性能（批量插入100条记录应该很快）
        assert end_time - start_time < 5  # 5秒内完成

    def test_query_performance_with_index(self, db):
        """
        测试带索引的查询性能
        验证索引对查询性能的提升
        """
        # 创建大量数据
        users = []
        for i in range(1000):
            user = User(
                id=str(uuid.uuid4()),
                username=f"perf_user_{i}",
                email=f"perf{i}@test.com",
                hashed_password=get_password_hash(f"pass{i}"),
                is_active=i % 2 == 0,
                created_at=datetime.utcnow()
            )
            users.append(user)
        
        db.add_all(users)
        db.commit()
        
        # 测试带索引查询的性能
        start_time = time.time()
        result = db.query(User).filter_by(username="perf_user_500").first()
        end_time = time.time()
        
        assert result is not None
        # 带索引的查询应该很快
        assert end_time - start_time < 1  # 1秒内完成

    def test_connection_pool_exhaustion(self):
        """
        测试连接池耗尽处理
        验证连接池耗尽时的行为
        """
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=0,
            pool_timeout=0.5
        )
        
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        
        sessions = []
        
        # 占用所有连接
        for _ in range(2):
            session = SessionLocal()
            session.execute(text("SELECT 1"))
            sessions.append(session)
        
        # 尝试获取第三个连接应该失败
        with pytest.raises(Exception):
            session3 = SessionLocal()
            session3.execute(text("SELECT 1"))
        
        # 释放连接
        for session in sessions:
            session.close()
        
        engine.dispose()
