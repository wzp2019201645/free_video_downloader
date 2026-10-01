import re

from pydantic import BaseModel, field_validator

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL.fullmatch(email) or len(email) > 254:
            raise ValueError("邮箱格式不正确")
        return email

    @field_validator("password")
    @classmethod
    def password_length(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 128:
            raise ValueError("密码需要 8 到 128 位")
        return value


class ConfirmCheckoutRequest(BaseModel):
    session_id: str

    @field_validator("session_id")
    @classmethod
    def session_id_shape(cls, value: str) -> str:
        session_id = value.strip()
        if not re.fullmatch(r"cs_[A-Za-z0-9_]+", session_id):
            raise ValueError("订单号不正确")
        return session_id
