from pydantic import BaseModel, ConfigDict, EmailStr, Field

# JOB SEEKER REGISTRATION
class UserRegister(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


# EMPLOYER REGISTRATION
class EmployerRegister(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )



# USER RESPONSE
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    account_status: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# LOGIN RESPONSE
class TokenResponse(BaseModel):
    access_token: str
    token_type: str