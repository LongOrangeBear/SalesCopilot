"""SalesCopilot Backend -- точка входа."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    from config import settings

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
