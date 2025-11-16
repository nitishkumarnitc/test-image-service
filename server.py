import json
from fastapi import FastAPI, HTTPException
import uvicorn
from src.handler import request_upload, complete_upload, get_image, delete_image_handler

app = FastAPI(title="MontyCloud Image Service - Local HTTP Adapter")

@app.post("/v1/images")
async def upload(req: dict):
    event = {"body": json.dumps(req)}
    res = request_upload(event)
    return json.loads(res["body"]) if res["statusCode"] < 400 else HTTPException(status_code=res["statusCode"], detail=json.loads(res['body']))

@app.post("/v1/images/{image_id}/complete")
async def complete(image_id: str):
    event = {"pathParameters": {"image_id": image_id}}
    res = complete_upload(event)
    return json.loads(res["body"]) if res["statusCode"] < 400 else HTTPException(status_code=res["statusCode"], detail=json.loads(res['body']))

@app.get("/v1/images/{image_id}")
async def view(image_id: str):
    event = {"pathParameters": {"image_id": image_id}}
    res = get_image(event)
    return json.loads(res["body"]) if res["statusCode"] < 400 else HTTPException(status_code=res["statusCode"], detail=json.loads(res['body']))

@app.delete("/v1/images/{image_id}")
async def delete(image_id: str):
    event = {"pathParameters": {"image_id": image_id}}
    res = delete_image_handler(event)
    return json.loads(res["body"]) if res["statusCode"] < 400 else HTTPException(status_code=res["statusCode"], detail=json.loads(res['body']))

if __name__ == '__main__':
    uvicorn.run("server:app", host="0.0.0.0", port=8080, log_level="info")
