import os

import uvicorn


DEFAULT_PORT = 8080


def get_port():
    raw_port = os.getenv(
        "PORT",
        str(DEFAULT_PORT),
    )

    try:
        port = int(raw_port)
    except ValueError as error:
        raise RuntimeError(
            "PORT 必須是整數"
        ) from error

    if not 1 <= port <= 65535:
        raise RuntimeError(
            "PORT 必須介於 1 到 65535"
        )

    return port


def main():
    uvicorn.run(
        "app.api.web:app",
        host="0.0.0.0",
        port=get_port(),
    )


if __name__ == "__main__":
    main()
