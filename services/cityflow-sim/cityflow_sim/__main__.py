import uvicorn

from .main import create_app


def main() -> None:
    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7001,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
