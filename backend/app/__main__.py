import uvicorn

from app.logging import configure_logging
from app.main import create_app
from app.settings import Settings


def main() -> None:
    settings = Settings()
    configure_logging("debug" if settings.log_level == "trace" else settings.log_level)
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
