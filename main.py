import os
import base64
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        for file in files:
            image_bytes = await file.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{file.content_type};base64,{base64_image}"
                }
            })
        
        # 优化提示词：给大模型下达明确的规格提取硬指标
        content_list.append({
            "type": "text",
            "text": (
                "仔细分析菜单图片，提取所有菜品并翻译为中文。输出严格的JSON，勿包含Markdown格式：\n"
                "{\n"
                "  \"detectedCurrency\": \"货币代码如 USD, CNY, TWD, GBP\",\n"
                "  \"menu\": {\n"
                "    \"分类名(如:饭类,面食,汤羹,海鲜,肉类,饮料)\": [\n"
                "      {\n"
                "        \"nameOrig\": \"原文菜名\",\n"
                "        \"nameZh\": \"中文翻译菜名\",\n"
                "        \"priceOriginal\": 纯数字原价(例如 6.5),\n"
                "        \"specifications\": [\"必须从菜单提取真实存在的规格、份量或冷热选项，例如: \\\"小份\\\", \\\"大份\\\" 或 \\\"Hot\\\", \\\"Iced\\\"。若无多规格则填 \\\"常规\\\"] ,\n"
                "        \"isSignature\": 布尔值(是否为招牌/特色菜),\n"
                "        \"keywords\": \"食材或语意关键词(如:海鲜,微辣)\"\n"
                "      }\n"
                "    ]\n"
                "  }\n"
                "}"
            )
        })

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "你是一个高精度菜单结构化解析器，必须精准提取菜单上的多重规格选项。"},
                {"role": "user", "content": content_list}
            ]
        )
        
        return {
            "status": "success",
            "data": response.choices[0].message.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
