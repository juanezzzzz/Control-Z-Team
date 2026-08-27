"""AgroIA Casanare — punto de ensamblaje de la app FastAPI.

Ejecutar en local (desde la raíz del proyecto):
    uvicorn agroia.main:app --reload --port 8000

Luego exponer con un túnel HTTPS (ngrok, cloudflared) para registrar el
webhook de Telegram, o desplegar en un servicio gestionado (Render,
Railway, Fly.io) que entregue una URL HTTPS. Ver README.md.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agroia.api.routers import agentes, productos, webhook
from agroia.core.config import settings, variables_faltantes


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgroIA Casanare — Backend",
        version="0.1.0",
        description="Orquestación de los 3 agentes (recepción, estructuración, ventas) sobre Telegram + Claude + Supabase.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(webhook.router)
    app.include_router(productos.router)
    app.include_router(agentes.router)

    @app.get("/", tags=["health"])
    def health():
        """Healthcheck. Reporta qué variables de entorno faltan (solo los
        nombres, nunca los valores) para poder diagnosticar un despliegue mal
        configurado sin entrar a los logs del proveedor."""
        faltantes = variables_faltantes()
        return {
            "status": "ok" if not faltantes else "configuracion_incompleta",
            "servicio": "AgroIA Casanare backend",
            "entorno": settings.APP_ENV,
            "variables_faltantes": faltantes,
        }

    return app


app = create_app()
