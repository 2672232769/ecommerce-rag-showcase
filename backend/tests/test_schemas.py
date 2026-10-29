"""
P1 数据校验模块测试
测试范围: Pydantic schemas 的数据校验逻辑
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.schemas import (
    UserRegister,
    UserLogin,
    ChangePasswordRequest,
    ChatRequest,
    SessionCreate,
    SessionUpdate,
)


class TestUserRegister:
    """用户注册校验"""

    def test_valid_register(self):
        """有效注册数据"""
        u = UserRegister(username="testuser", password="123456")
        assert u.username == "testuser"
        assert u.password == "123456"

    def test_username_too_short(self):
        """用户名太短"""
        with pytest.raises(Exception):
            UserRegister(username="a", password="123456")

    def test_password_too_short(self):
        """密码太短"""
        with pytest.raises(Exception):
            UserRegister(username="test", password="123")

    def test_username_max_length(self):
        """用户名在最小长度边界"""
        u = UserRegister(username="ab", password="123456")
        assert u.username == "ab"


class TestUserLogin:
    """登录数据校验"""

    def test_valid_login(self):
        """有效登录数据"""
        u = UserLogin(username="admin", password="123456")
        assert u.username == "admin"

    def test_missing_fields_raises_error(self):
        """缺少字段抛出异常"""
        with pytest.raises(Exception):
            UserLogin()  # 缺少必填字段


class TestChangePasswordRequest:
    """改密请求校验"""

    def test_valid_request(self):
        req = ChangePasswordRequest(old_password="old", new_password="new123")
        assert req.old_password == "old"
        assert req.new_password == "new123"

    def test_new_password_too_short(self):
        with pytest.raises(Exception):
            ChangePasswordRequest(old_password="old", new_password="12")


class TestChatRequest:
    """聊天请求校验"""

    def test_valid_request(self):
        req = ChatRequest(session_id=1, question="你好")
        assert req.session_id == 1
        assert req.question == "你好"

    def test_empty_question(self):
        """空问题应被拒绝"""
        with pytest.raises(Exception):
            ChatRequest(session_id=1, question="")

    def test_question_max_length(self):
        """问题长度上限"""
        long_q = "你好" * 2500  # 接近 5000 字符上限
        req = ChatRequest(session_id=1, question=long_q)
        assert req.question == long_q

    def test_question_too_long(self):
        """超过 5000 字符上限"""
        with pytest.raises(Exception):
            ChatRequest(session_id=1, question="好" * 5001)


class TestSessionCreate:
    """会话创建校验"""

    def test_default_title(self):
        s = SessionCreate()
        assert s.title == "新对话"

    def test_custom_title(self):
        s = SessionCreate(title="Hello World")
        assert s.title == "Hello World"
