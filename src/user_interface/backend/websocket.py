"""
WebSocket接口
提供实时行情推送服务
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from data_management.data_query.query_manager import query_manager

from .dependencies import verify_api_key

logger = logging.getLogger(__name__)

ws_router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # key: 股票代码, value: 连接列表
        self.subscriptions: Dict[WebSocket, List[str]] = {}  # key: 连接, value: 订阅的股票代码列表
        self.running = False
        self.push_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        self.subscriptions[websocket] = []
        logger.info(f"新WebSocket连接建立，客户端：{websocket.client.host}")

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        # 清理订阅
        if websocket in self.subscriptions:
            for stock_code in self.subscriptions[websocket]:
                if stock_code in self.active_connections and websocket in self.active_connections[stock_code]:
                    self.active_connections[stock_code].remove(websocket)
                    if not self.active_connections[stock_code]:
                        del self.active_connections[stock_code]
            del self.subscriptions[websocket]
        logger.info(f"WebSocket连接断开，客户端：{websocket.client.host}")

    async def subscribe(self, websocket: WebSocket, stock_codes: List[str]):
        """订阅股票行情"""
        if websocket not in self.subscriptions:
            return

        for code in stock_codes:
            if code not in self.subscriptions[websocket]:
                self.subscriptions[websocket].append(code)
                if code not in self.active_connections:
                    self.active_connections[code] = []
                if websocket not in self.active_connections[code]:
                    self.active_connections[code].append(websocket)

        logger.info(f"客户端{websocket.client.host}订阅股票：{stock_codes}，当前订阅：{self.subscriptions[websocket]}")

        # 启动推送任务
        if not self.running:
            self.running = True
            self.push_task = asyncio.create_task(self._push_loop())

    async def unsubscribe(self, websocket: WebSocket, stock_codes: List[str]):
        """取消订阅"""
        if websocket not in self.subscriptions:
            return

        for code in stock_codes:
            if code in self.subscriptions[websocket]:
                self.subscriptions[websocket].remove(code)
                if code in self.active_connections and websocket in self.active_connections[code]:
                    self.active_connections[code].remove(websocket)
                    if not self.active_connections[code]:
                        del self.active_connections[code]

        logger.info(
            f"客户端{websocket.client.host}取消订阅股票：{stock_codes}，当前订阅：{self.subscriptions[websocket]}"
        )

        # 如果没有订阅了，停止推送任务
        if not self.active_connections and self.push_task:
            self.running = False
            self.push_task.cancel()
            self.push_task = None

    async def _push_loop(self):
        """实时推送循环"""
        logger.info("实时行情推送任务启动")
        while self.running:
            try:
                if not self.active_connections:
                    self.running = False
                    break

                # 获取所有订阅的股票代码
                stock_codes = list(self.active_connections.keys())
                if not stock_codes:
                    await asyncio.sleep(1)
                    continue

                # 查询实时行情
                result = query_manager.get_realtime_quote(stock_codes)
                if not result.success or result.data.empty:
                    await asyncio.sleep(1)
                    continue

                df = result.to_df()
                # 按股票代码分组推送
                for _, row in df.iterrows():
                    stock_code = row["stock_code"]
                    if stock_code not in self.active_connections:
                        continue

                    message = json.dumps(
                        {"type": "realtime_quote", "data": row.to_dict(), "timestamp": datetime.now().isoformat()},
                        ensure_ascii=False,
                        default=str,
                    )

                    # 推送给所有订阅该股票的连接
                    for connection in self.active_connections[stock_code]:
                        try:
                            await connection.send_text(message)
                        except Exception as e:
                            logger.error(f"推送消息失败：{e}")
                            self.disconnect(connection)

                # 每秒推送一次
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"推送任务异常：{e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info("实时行情推送任务停止")


manager = ConnectionManager()


@ws_router.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket, api_key: Optional[str] = Query(None, description="API Key")):
    """
    实时行情WebSocket接口
    消息格式：
    - 订阅：{"action": "subscribe", "stock_codes": ["000001.SZ", "600000.SH"]}
    - 取消订阅：{"action": "unsubscribe", "stock_codes": ["000001.SZ"]}
    """
    # 验证API Key
    from common.config import settings
    from common.utils import CryptoUtils

    if settings.API_KEY_ENABLED:
        if not api_key or not CryptoUtils.verify_api_key(api_key):
            await websocket.close(code=1008, reason="无效的API Key")
            return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")
                stock_codes = message.get("stock_codes", [])

                if action == "subscribe" and stock_codes:
                    await manager.subscribe(websocket, stock_codes)
                    await websocket.send_json({"type": "system", "message": f"成功订阅股票：{stock_codes}"})
                elif action == "unsubscribe" and stock_codes:
                    await manager.unsubscribe(websocket, stock_codes)
                    await websocket.send_json({"type": "system", "message": f"成功取消订阅股票：{stock_codes}"})
                else:
                    await websocket.send_json({"type": "error", "message": "无效的消息格式"})

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "无效的JSON格式"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket异常：{e}", exc_info=True)
        manager.disconnect(websocket)
