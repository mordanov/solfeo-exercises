from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class UploadLimit:
    def __init__(self, app: ASGIApp, maximum: int) -> None:
        self.app = app
        self.maximum = maximum

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        length = headers.get(b"content-length")
        if length and (not length.isdigit() or int(length) > self.maximum):
            await JSONResponse(
                {"error": "FILE_TOO_LARGE"},
                status_code=413,
                headers={"Cache-Control": "no-store"},
            )(scope, receive, send)
            return
        size = 0

        async def limited_receive() -> Message:
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > self.maximum:
                raise HTTPException(413)
            return message

        await self.app(scope, limited_receive, send)
