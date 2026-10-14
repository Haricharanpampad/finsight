from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt only uses the first 72 bytes
    business_name: str = Field(min_length=1, max_length=160)
    business_type: str = Field(default="General", max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_name: str
    business_type: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    business: BusinessOut | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
