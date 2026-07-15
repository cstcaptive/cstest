import os
import base64
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI()

# 配置 CORS 跨域，确保前端顺利调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全地从 Render 的环境变量中读取敏感信息
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)

@app.get("/")
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Backend is ready, but index.html is missing"}

# 【核心修复】修改路径，完美对齐前端的调用地址
@app.post("/api/parse-menu")
async def parse_menu_files(files: List[UploadFile] = File(...)):
    try:
        content_list = []
        
        # 遍历并处理上传的图片文件
        for file in files:
            image_bytes = await file.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{file.content_type};base64,{base64_image}"
                }
            })
        
        # 结合你的业务提示词
        content_list.append({
            "type": "text",
            "text": "请帮我提取并解析这张图片中的内容。"
        })

        # 调用大模型
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个方便点餐和购物的智能助手，负责帮我解析内容并转换为结构化数据。"},
                {"role": "user", "content": content_list}
            ]
        )
        return {"result": response.choices[0].message.content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
