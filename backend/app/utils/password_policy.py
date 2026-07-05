"""统一密码强度策略。"""

import re

from app.exceptions import ValidationError

_PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")


def validate_password_strength(password: str, field: str = "password") -> None:
    """
    校验密码强度：至少 8 位，且同时包含字母和数字。

    注册、修改密码等入口必须复用同一策略，避免弱口令绕过。
    """
    if not _PASSWORD_PATTERN.match(password or ""):
        raise ValidationError(
            message="密码强度不足：至少8个字符，且必须包含大小写字母、数字和特殊字符",
            field=field,
        )
