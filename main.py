import os
import base64
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI()

# 配置 CORS 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 读取环境变量
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)

@app.get("/")
async def serve_frontend():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Backend is ready, but index.html is missing"}

@app.post("/api/parse-menu")
async def parse_menu_files(files: List[UploadFile] = File(...)):
    try:
        content_list = []
        
        # 遍历处理图片
        for file in files:
            image_bytes = await file.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{file.content_type};base64,{base64_image}"
                }
            })
        
        # 给出极其严苛的 JSON 结构限制提示词
        content_list.append({
            "type": "text",
            "text": (
                "请仔细分析这张菜单图片，提取所有的菜品并翻译为中文。"
                "你必须输出一个符合以下结构的 JSON 对象，不要包含任何解释性文本或 Markdown 标记：\n"
                "{\n"
                "  \"detectedCurrency\": \"三位货币代码，例如 USD, GBP, EUR, CNY 等\",\n"
                "  \"menu\": {\n"
                "    \"主菜/饮料/甜点等分类名\": [\n"
                "      {\n"
                "        \"nameOrig\": \"英文或原文菜名\",\n"
                "        \"nameZh\": \"中文翻译菜名\",\n"
                "        \"priceOriginal\": 数字类型的原价(注意：只要纯数字，不要带任何货币符号，例如 6.50),\n"
                "        \"tags\": [\"标签1\", \"标签2\"],\n"
                "        \"isAiRecommended\": 布尔值(根据菜品特色决定是否推荐，true 或 false),\n"
                "        \"aiReason\": \"推荐理由，如果不推荐则为空字符串\"\n"
                "      }\n"
                "    ]\n"
                "  }\n"
                "}"
            )
        })

        # 调用大模型，并强制开启 JSON Mode 确保返回 100% 合法的 JSON
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "你是一个高度专业、只输出标准 JSON 数据的智能点餐助手。"},
                {"role": "user", "content": content_list}
            ]
        )
        
        # 【完美对齐前端】返回前端日思夜想的 status 和 data 外壳
        return {
            "status": "success",
            "data": response.choices[0].message.content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
