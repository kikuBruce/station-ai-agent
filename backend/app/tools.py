from __future__ import annotations

import asyncio
import os
from typing import List, Dict, Any

import aiosqlite
from bs4 import BeautifulSoup
import html5lib

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "demo.db")


async def ensure_demo_db() -> None:
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	if os.path.exists(DB_PATH):
		return
	async with aiosqlite.connect(DB_PATH) as db:
		await db.executescript(
			"""
			CREATE TABLE sales (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				category TEXT NOT NULL,
				amount REAL NOT NULL
			);
			INSERT INTO sales (category, amount) VALUES
			('电子产品', 15230.5),
			('家用电器', 10890.0),
			('服饰鞋帽', 9320.8),
			('食品饮料', 12560.2),
			('运动户外', 6840.1),
			('美妆个护', 8720.4);
			"""
		)
		await db.commit()


async def run_sql_query_tool(sql: str) -> List[Dict[str, Any]]:
	# Read-only guard
	for keyword in ("insert", "update", "delete", "drop", "alter", "create"):
		if keyword in sql.lower():
			raise ValueError("Only read-only SELECT queries are permitted")
	async with aiosqlite.connect(DB_PATH) as db:
		db.row_factory = aiosqlite.Row
		async with db.execute(sql) as cursor:
			rows = await cursor.fetchall()
			return [dict(row) for row in rows]


async def validate_html_tool(html: str) -> Dict[str, Any]:
	# Use html5lib to parse and report basic issues via BeautifulSoup
	soup = BeautifulSoup(html, "html5lib")
	errors: List[str] = []
	# Simple heuristic checks
	if not soup.find():
		errors.append("无法解析 HTML 内容")
	if soup.find_all(string=lambda s: isinstance(s, str) and "<script" in s.lower()):
		errors.append("检测到原始脚本标记文本，可能存在注入风险")

	# Check for missing lang attribute in html tag
	html_tag = soup.find("html")
	if html_tag and not html_tag.get("lang"):
		errors.append("<html> 标签缺少 lang 属性")

	# Collect outline of tags
	outline: List[str] = []
	for tag in soup.find_all(True):
		outline.append(tag.name)

	return {
		"valid": len(errors) == 0,
		"errors": errors,
		"outline": outline[:50],
	}