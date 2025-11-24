# server.py
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

from src.handler import (
    request_upload,
    complete_upload,
    get_image,
    delete_image_handler,
    list_images_handler,
)

app = FastAPI(title="MontyCloud Image Service - Local HTTP Adapter")


def _unwrap_handler_response(res: dict):
    """
    Convert handler-style response {"statusCode": int, "body": "<json>"} into
    a FastAPI JSONResponse (with parsed JSON body and proper status code).
    """
    status = int(res.get("statusCode", 500))
    body = res.get("body")
    # body may already be dict (if someone changed handler). ensure it's a dict/object.
    if isinstance(body, str):
        try:
            body_obj = json.loads(body)
        except Exception:
            # if it's plain string, return as {"message": body}
            body_obj = {"message": body}
    else:
        body_obj = body
    return JSONResponse(content=body_obj, status_code=status)


@app.post("/v1/images")
async def upload(req: dict):
    event = {"body": json.dumps(req)}
    res = request_upload(event)
    return _unwrap_handler_response(res)


@app.post("/v1/images/{image_id}/complete")
async def complete(image_id: str):
    event = {"pathParameters": {"image_id": image_id}}
    res = complete_upload(event)
    return _unwrap_handler_response(res)


@app.get("/v1/images/{image_id}")
async def view(image_id: str, request: Request):
    qs = dict(request.query_params)
    event = {"pathParameters": {"image_id": image_id}, "queryStringParameters": qs}
    res = get_image(event)
    return _unwrap_handler_response(res)


@app.get("/v1/images")
async def list_images(request: Request):
    qs = dict(request.query_params)
    event = {"queryStringParameters": qs}
    res = list_images_handler(event)
    return _unwrap_handler_response(res)


@app.delete("/v1/images/{image_id}")
async def delete(image_id: str):
    event = {"pathParameters": {"image_id": image_id}}
    res = delete_image_handler(event)
    return _unwrap_handler_response(res)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080, log_level="info")
