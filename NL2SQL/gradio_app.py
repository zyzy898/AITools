import gradio as gr
import requests
import pymysql
import os
import json
import re
import threading
import time
from pymysql import Error
from dbutils.pooled_db import PooledDB
from typing import Optional, Tuple, List, Dict, Any

# ================= 配置 =================
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["ALL_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["all_proxy"] = ""

session = requests.Session()
session.trust_env = False

DB_CONFIG = {
    "host": "",
    "user": "",
    "password": "",
    "database": "",
    "port": 3306,
    "charset": "utf8mb4",
}
OLLAMA_MODEL = "hf.co/Qwen/Qwen3-8B-GGUF:Q8_0"
OLLAMA_URL = "http://localhost:11434/api/generate"

# 表结构缓存 (schema, timestamp)
_schema_cache: Tuple[str, float] = ("", 0.0)
CACHE_TTL = 60.0

# 连接池
_db_pool: Optional[PooledDB] = None
_schema_pool: Optional[PooledDB] = None


def get_pool() -> PooledDB:
    global _db_pool
    if _db_pool is None:
        _db_pool = PooledDB(
            creator=pymysql,
            maxconnections=10,
            mincached=2,
            maxcached=5,
            blocking=True,
            **DB_CONFIG,
        )
    return _db_pool


def get_schema_pool() -> PooledDB:
    global _schema_pool
    if _schema_pool is None:
        _schema_pool = PooledDB(
            creator=pymysql,
            maxconnections=3,
            mincached=1,
            maxcached=2,
            blocking=True,
            cursorclass=pymysql.cursors.DictCursor,
            **DB_CONFIG,
        )
    return _schema_pool


def get_db_connection():
    try:
        return get_pool().connection()
    except Error as e:
        return f"数据库连接失败: {e}"


def get_schema_connection():
    try:
        return get_schema_pool().connection()
    except Error as e:
        return f"数据库连接失败: {e}"


def get_database_schema() -> str:
    global _schema_cache
    cached_schema, cached_time = _schema_cache
    if cached_schema and (time.time() - cached_time) < CACHE_TTL:
        return cached_schema

    connection = get_schema_connection()
    if isinstance(connection, str):
        return connection

    schema_str = ""
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        for table in tables:
            table_name = list(table.values())[0]
            schema_str += f"【表名：{table_name}】\n"
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            for col in columns:
                col_name = col["Field"]
                col_type = col["Type"]
                key = col["Key"]
                schema_str += f"  - {col_name} ({col_type})"
                if key == "PRI":
                    schema_str += " [主键]"
                if col["Null"] == "YES":
                    schema_str += " [可空]"
                if col["Default"]:
                    schema_str += f" 默认值:{col['Default']}"
                schema_str += "\n"
            cursor.execute(f"SHOW INDEX FROM `{table_name}`")
            indexes = cursor.fetchall()
            for idx in indexes:
                if idx["Key_name"] != "PRIMARY":
                    schema_str += (
                        f"  - 索引: {idx['Key_name']} ON ({idx['Column_name']})\n"
                    )
            schema_str += "\n"

        _schema_cache = (schema_str, time.time())
        return schema_str
    except Error as e:
        return f"ERROR: 获取表结构失败: {e}"
    finally:
        if connection:
            connection.close()


def validate_sql(sql: str) -> Tuple[bool, str]:
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return False, "只允许执行 SELECT 查询语句"
    dangerous = re.findall(
        r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b",
        sql_upper,
    )
    if dangerous:
        return False, f"禁止的 SQL 关键字: {', '.join(dangerous)}"
    return True, ""


def nl_to_sql_stream(user_prompt: str, table_schema: str):
    prompt = f"""你是一个专业的MySQL SQL生成助手。根据以下数据库表结构，将用户的自然语言问题转换为标准MySQL SELECT语句。

【数据库表结构】
{table_schema}

【要求】
1. 先用中文解释你的分析思路
2. 然后生成SQL语句
3. 只生成SELECT查询语句
4. 格式：【思考】<分析>【SQL】<SQL语句>

【用户问题】
{user_prompt}

请按格式回答："""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "temperature": 0.1,
    }

    try:
        response = session.post(OLLAMA_URL, json=payload, timeout=120, stream=True)
        response.raise_for_status()

        full_response = ""
        full_thinking = ""
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                json_data = json.loads(data)
                token = json_data.get("response", "")
                thinking = json_data.get("thinking", "")

                if thinking:
                    full_thinking += thinking
                if token:
                    full_response += token

                sql = ""
                thinking_out = full_thinking
                if "【SQL】" in full_response:
                    parts = full_response.split("【SQL】")
                    thinking_out = parts[0].replace("【思考】", "").strip()
                    sql = parts[1].strip() if len(parts) > 1 else full_response

                yield thinking_out, sql
    except requests.exceptions.Timeout:
        yield "请求超时", ""
    except Exception as e:
        yield f"错误: {str(e)}", ""


def nl_to_sql(user_prompt: str, table_schema: str) -> str:
    prompt = f"""你是一个专业的 MySQL SQL 生成助手。根据以下数据库表结构，将用户的自然语言问题转换为标准 MySQL SELECT 语句。

【数据库表结构】
{table_schema}

【要求】
1. 只返回 SQL 语句，不要任何解释或多余文字
2. MySQL 语法，表名和字段名必须匹配表结构
3. 如果无法转换，返回 "ERROR: 无法生成对应的 SQL"
4. 只生成 SELECT 查询语句

【用户问题】
{user_prompt}

【SQL 语句】
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.1,
    }

    try:
        response = session.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        sql = response.json().get("response", "").strip()
        sql = re.sub(r"```sql\s*", "", sql).replace("```", "").strip()
        return sql
    except requests.exceptions.Timeout:
        return "ERROR: Ollama 请求超时"
    except Exception as e:
        return f"ERROR: {str(e)}"


def execute_sql(sql: str) -> Tuple[str, List[List[Any]], Optional[List[str]]]:
    valid, msg = validate_sql(sql)
    if not valid:
        return msg, [], None

    connection = get_db_connection()
    if isinstance(connection, str):
        return connection, [], None

    try:
        cursor = connection.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        table_data = []
        for row in results:
            processed_row = [str(value) if value is not None else None for value in row]
            table_data.append(processed_row)

        return "查询成功", table_data, columns
    except Error as e:
        return f"SQL 执行失败: {e}", [], None
    finally:
        if connection:
            connection.close()


def main_app(user_prompt: str):
    if not user_prompt or not user_prompt.strip():
        return "请输入问题", "", "", None

    table_schema = get_database_schema()
    if isinstance(table_schema, str) and table_schema.startswith("ERROR"):
        return f"数据库错误: {table_schema}", "", "", None

    final_sql = ""
    final_thinking = ""
    sql_generator = nl_to_sql_stream(user_prompt, table_schema)

    for thinking, sql_chunk in sql_generator:
        final_thinking = thinking
        final_sql = sql_chunk
        if thinking.startswith("错误") or sql_chunk.startswith("错误"):
            yield sql_chunk, thinking, sql_chunk, None
        else:
            yield "正在生成 SQL...", thinking, sql_chunk, None

    if final_sql.startswith("错误") or final_sql.startswith("ERROR"):
        yield f"SQL生成错误: {final_sql}", final_thinking, final_sql, None
        return

    status, data, headers = execute_sql(final_sql)

    if "失败" in status or (isinstance(data, list) and len(data) == 0):
        yield status, final_thinking, final_sql, None
        return

    yield status, final_thinking, final_sql, {"headers": headers, "data": data}


# 构建 Gradio 界面
with gr.Blocks(title="自然语言转 SQL 助手") as demo:
    gr.Markdown("# 🗣️ 自然语言转 SQL 查询系统")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 💬 你的问题")
            input_text = gr.Textbox(
                label="输入自然语言查询",
                placeholder="例如：查询语文成绩大于80分的学生姓名和总分",
                lines=3,
            )
            submit_btn = gr.Button("🚀 转换并查询", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### 📝 结果展示")
            status_box = gr.Textbox(label="状态", interactive=False)
            thinking_box = gr.Textbox(label="思考流程", lines=5, interactive=False)
            sql_box = gr.Textbox(label="生成的 SQL", lines=4, interactive=False)
            output_table = gr.Dataframe(label="查询结果", interactive=False)

    with gr.Row():
        gr.Markdown(
            "### 💡 示例查询\n"
            "- 查询物理成绩最高的5名学生\n"
            "- 查找体脂率大于20%的男生\n"
            "- 统计每个学科的平均分\n"
            "- 查询王强家的联系电话"
        )

    submit_btn.click(
        fn=main_app,
        inputs=input_text,
        outputs=[status_box, thinking_box, sql_box, output_table],
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
