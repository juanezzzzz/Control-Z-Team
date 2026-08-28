from pydantic import BaseModel


class LoginIn(BaseModel):
    usuario: str
    contrasena: str


class LoginOut(BaseModel):
    token: str


class CambiarEstadoIn(BaseModel):
    estado: str  # "activo" | "vendido" | "inactivo"
