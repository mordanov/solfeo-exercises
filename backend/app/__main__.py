import uvicorn

from app.main import create_app
from app.settings import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        create_app(),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
