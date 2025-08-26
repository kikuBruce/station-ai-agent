from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .tools import run_sql_query_tool, validate_html_tool, ensure_demo_db

app = FastAPI(title="AI Chat Service", version="0.1.0")

# CORS for local dev
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
	await ensure_demo_db()


def sse_encode(data: Dict[str, Any]) -> str:
	return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def ai_stream_emulator(payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
	"""
	Emulates an AI model that interleaves markdown text and tool JSON blocks.
	The frontend parser will detect tool JSON and render accordingly.
	"""
	user_content = (payload.get("content") or "").strip()
	if not user_content:
		yield sse_encode({"type": "done"})
		return

	# Intro markdown
	intro = "正在处理你的请求…\n\n下面是为你生成的报表与说明：\n"
	for ch in intro:
		await asyncio.sleep(0.005)
		yield sse_encode({"type": "token", "text": ch})

	# Example: run SQL query tool if user asks about sales
	if "销售" in user_content or "sales" in user_content.lower():
		tool_block = {
			"type": "tool",
			"name": "db_query",
			"status": "running",
			"data": {
				"sql": "SELECT category, SUM(amount) AS total FROM sales GROUP BY category ORDER BY total DESC LIMIT 5;"
			}
		}
		yield sse_encode(tool_block)
		rows = await run_sql_query_tool(tool_block["data"]["sql"])  # list of dicts
		result_block = {
			"type": "tool",
			"name": "db_query",
			"status": "success",
			"data": {
				"columns": list(rows[0].keys()) if rows else [],
				"rows": rows,
				"chart": {
					"type": "echarts",
					"option": {
						"title": {"text": "各品类销售额Top5"},
						"tooltip": {},
						"xAxis": {"type": "category", "data": [r["category"] for r in rows]},
						"yAxis": {"type": "value"},
						"series": [{"type": "bar", "data": [r["total"] for r in rows]}],
					}
				}
			}
		}
		yield sse_encode(result_block)

	# Example: validate HTML snippet tool if message looks like HTML
	if "<" in user_content and ">" in user_content:
		tool_block2 = {
			"type": "tool",
			"name": "html_validate",
			"status": "running",
			"data": {"html": user_content}
		}
		yield sse_encode(tool_block2)
		validation = await validate_html_tool(user_content)
		yield sse_encode({
			"type": "tool",
			"name": "html_validate",
			"status": "success",
			"data": validation,
		})

	# Outro markdown
	outro = "\n\n以上为自动生成内容。如需刷新方案，请点击下方刷新按钮。"
	for ch in outro:
		await asyncio.sleep(0.005)
		yield sse_encode({"type": "token", "text": ch})

	yield sse_encode({"type": "done"})


@app.post("/chat")
async def chat(request: Request) -> StreamingResponse:
	payload = await request.json()

	async def event_generator() -> AsyncGenerator[bytes, None]:
		async for chunk in ai_stream_emulator(payload):
			yield chunk.encode("utf-8")

	return StreamingResponse(event_generator(), media_type="text/event-stream")