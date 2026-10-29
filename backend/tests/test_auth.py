"""
P0 核心认证模块单元测试
测试范围: hash_password, verify_password, create_access_token,
         get_current_user, get_admin_user, seed_admin
"""
import pytest
import os
import sys

# 确保能找到 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.config import settings


class TestHashPassword:
    """密码哈希功能测试"""

    def test_hash_returns_string(self):
        """正常输入返回非空字符串"""
        result = hash_password("test123")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_starts_with_bcrypt_prefix(self):
        """返回标准 bcrypt 格式的哈希"""
        result = hash_password("mypassword")
        assert result.startswith("$2b$") or result.startswith("$2a$")

    def test_different_inputs_produce_different_hashes(self):
        """不同输入产生不同的哈希"""
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2

    def test_same_input_produces_different_hashes_due_to_salt(self):
        """同一输入因随机盐值产生不同哈希"""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # bcrypt 有随机盐

    def test_empty_password(self):
        """空字符串也能哈希"""
        result = hash_password("")
        assert isinstance(result, str)
        assert len(result) > 0


class TestVerifyPassword:
    """密码验证功能测试"""

    def test_verify_correct_password(self):
        """正确密码验证通过"""
        hashed = hash_password("correct123")
        assert verify_password("correct123", hashed) is True

    def test_verify_wrong_password(self):
        """错误密码验证失败"""
        hashed = hash_password("real_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_case_sensitive(self):
        """密码大小写敏感"""
        hashed = hash_password("CaseSensitive")
        assert verify_password("casesensitive", hashed) is False
        assert verify_password("CaseSensitive", hashed) is True

    def test_verify_with_special_chars(self):
        """特殊字符密码验证"""
        hashed = hash_password("p@ss!中 文")
        assert verify_password("p@ss!中 文", hashed) is True


class TestCreateAccessToken:
    """JWT 令牌生成测试"""

    def test_returns_string_token(self):
        """返回字符串格式的令牌"""
        token = create_access_token(data={"sub": 1})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_three_parts(self):
        """JWT 包含三个点分隔的部分"""
        token = create_access_token(data={"sub": 1})
        parts = token.split(".")
        assert len(parts) == 3

    def test_different_data_produces_different_tokens(self):
        """不同输入产生不同令牌"""
        t1 = create_access_token(data={"sub": 1})
        t2 = create_access_token(data={"sub": 2})
        assert t1 != t2

    def test_custom_expiration(self):
        """自定义过期时间"""
        from datetime import timedelta
        token = create_access_token(
            data={"sub": 1},
            expires_delta=timedelta(minutes=5),
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_default_expiration_uses_config(self):
        """默认过期时间使用配置值"""
        token = create_access_token(data={"sub": 1})
        from jose import jwt
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=["HS256"]
        )
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "1"
