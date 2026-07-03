"""COSA socket.io (engine.io v3) istemcisi — gercek-zamanli durum + komut.

Cerceveleme:
  "0{sid,pingInterval}"  -> engine OPEN
  ">> 40"                -> namespace connect (biz)
  "40"                   -> namespace connected (server)
  "42<ackid>[method,req]"-> RPC istegi (biz)  ; url=/api/... , headers.authToken
  "43<ackid>[{body,..}]" -> RPC yaniti (server)
  "42[\"endpoint\",{data,id}]" -> UNSOLICITED push (delta)
  ">> 2" / "<< 3"        -> engine ping/pong (EIO3'te client ping atar)
Auth: her RPC header'inda authToken (REST login'den).
Dis sicaklik: /api/places/getPlace periyodik cekilir (hava-durumu currently.temperature).
"""
from __future__ import annotations

import asyncio
import json

import aiohttp

from .api import PROVIDER, cosa_login, endpoint_to_ha_state
from .const import LOGGER

SOCKET_URL = (
    "wss://kiwi.cosa.com.tr/socket.io/"
    "?__sails_io_sdk_version=0.11.0&__sails_io_sdk_platform=browser"
    "&__sails_io_sdk_language=javascript&EIO=3&transport=websocket"
)

RPC_TIMEOUT = 15
PLACE_REFRESH = 900  # sn (dis sicaklik yenileme araligi)


class CosaSocketClient:
    """Kalici socket.io baglantisi; durumu tutar, komut gonderir."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ack = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._raw: dict[str, dict] = {}
        self.endpoints: dict[str, str] = {}
        self._place: dict[str, str] = {}     # ep_id -> place_id
        self._outside: dict[str, float] = {}  # ep_id -> dis sicaklik
        self._callback = None
        self._task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._place_task: asyncio.Task | None = None
        self._send_lock = asyncio.Lock()
        self._closing = False
        self._first_data = asyncio.Event()

    def set_callback(self, cb) -> None:
        self._callback = cb

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def wait_ready(self, timeout: float = 30) -> None:
        await asyncio.wait_for(self._first_data.wait(), timeout)

    async def stop(self) -> None:
        self._closing = True
        for t in (self._ping_task, self._place_task):
            if t:
                t.cancel()
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        if self._task:
            self._task.cancel()

    # ---- baglanti dongusu ----
    async def _run(self) -> None:
        backoff = 2
        while not self._closing:
            try:
                if not self._token:
                    self._token = await cosa_login(self._session, self._email, self._password)
                await self._serve()
                backoff = 2
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                LOGGER.warning("Cosa socket hata: %s; %ds sonra yeniden baglaniyor", err, backoff)
            self._fail_pending()
            if self._closing:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    async def _serve(self) -> None:
        async with self._session.ws_connect(
            SOCKET_URL, headers={"Origin": "null"}, heartbeat=None
        ) as ws:
            self._ws = ws
            LOGGER.debug("Cosa socket baglandi")
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._on_frame(msg.data)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        self._ws = None
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None

    async def _on_frame(self, d: str) -> None:
        if d.startswith("0") and not d.startswith("40"):
            info = json.loads(d[1:])
            interval = info.get("pingInterval", 25000) / 1000
            await self._raw_send("40")
            self._ping_task = asyncio.create_task(self._ping_loop(interval))
        elif d.startswith("40"):
            asyncio.create_task(self._subscribe_all())
        elif d == "3":
            pass
        elif d == "2":
            await self._raw_send("3")
        elif d.startswith("43"):
            i = 2
            while i < len(d) and d[i].isdigit():
                i += 1
            ackid = int(d[2:i]) if i > 2 else 0
            fut = self._pending.get(ackid)
            if fut is not None and not fut.done():
                fut.set_result(json.loads(d[i:]))
        elif d.startswith("42"):
            payload = json.loads(d[2:])
            if payload and payload[0] == "endpoint":
                self._apply_push(payload[1])

    async def _ping_loop(self, interval: float) -> None:
        try:
            while True:
                await asyncio.sleep(interval)
                if self._ws is not None and not self._ws.closed:
                    await self._raw_send("2")
        except asyncio.CancelledError:
            pass

    # ---- RPC ----
    async def _raw_send(self, text: str) -> None:
        async with self._send_lock:
            if self._ws is None or self._ws.closed:
                raise RuntimeError("socket kapali")
            await self._ws.send_str(text)

    async def _rpc(self, method: str, url: str, data: dict | None = None) -> dict:
        ackid = self._ack
        self._ack += 1
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[ackid] = fut
        req = [
            method,
            {
                "method": method,
                "headers": {
                    "Accept": "application/json, text/plain, */*",
                    "authToken": self._token,
                    "provider": PROVIDER,
                    "Content-Type": "application/json;charset=utf-8",
                },
                "data": data or {},
                "url": url,
            },
        ]
        try:
            await self._raw_send(f"42{ackid}{json.dumps(req)}")
            resp = await asyncio.wait_for(fut, RPC_TIMEOUT)
        finally:
            self._pending.pop(ackid, None)
        return resp[0] if resp else {}

    def _fail_pending(self) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(RuntimeError("socket kapandi"))
        self._pending.clear()

    # ---- subscribe + push ----
    async def _subscribe_all(self) -> None:
        try:
            resp = await self._rpc("get", "/api/endpoints/getEndpoints")
            eps = (resp.get("body") or {}).get("endpoints", [])
            self.endpoints = {e["id"]: e["name"] for e in eps}
            for ep_id in self.endpoints:
                r2 = await self._rpc("post", "/api/endpoints/getEndpoint", {"endpoint": ep_id})
                full = (r2.get("body") or {}).get("endpoint")
                if full:
                    self._raw[ep_id] = full
                    if full.get("place"):
                        self._place[ep_id] = full["place"]
                    self._emit(ep_id)
            await self._refresh_places()
            if self._place_task is None:
                self._place_task = asyncio.create_task(self._place_loop())
            self._first_data.set()
        except Exception as err:  # noqa: BLE001
            LOGGER.warning("Cosa subscribe hatasi: %s", err)

    async def _refresh_places(self) -> None:
        for ep_id, place_id in dict(self._place).items():
            try:
                resp = await self._rpc("post", "/api/places/getPlace", {"place": place_id})
                cur = ((resp.get("body") or {}).get("place") or {}).get("currently") or {}
                if cur.get("temperature") is not None:
                    self._outside[ep_id] = cur["temperature"]
                    self._emit(ep_id)
            except Exception as err:  # noqa: BLE001
                LOGGER.debug("getPlace hata: %s", err)

    async def _place_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(PLACE_REFRESH)
                await self._refresh_places()
        except asyncio.CancelledError:
            pass

    def _apply_push(self, evt: dict) -> None:
        ep_id = evt.get("id")
        data = evt.get("data") or {}
        if ep_id is None:
            return
        self._raw.setdefault(ep_id, {}).update(data)
        self._emit(ep_id)

    def _emit(self, ep_id: str) -> None:
        if self._callback is not None:
            ha = endpoint_to_ha_state(self._raw[ep_id])
            ha["outside_temperature"] = self._outside.get(ep_id)
            self._callback(ep_id, self.endpoints.get(ep_id, "Klima"), ha)

    # ---- komut ----
    async def send_ac_state(self, ep_id: str, field: str, value: int) -> None:
        resp = await self._rpc(
            "post", "/api/endpoints/sendACState",
            {"type": field, "value": value, "endpoint": ep_id},
        )
        body = resp.get("body") or {}
        if body.get("ok") != 1:
            if resp.get("statusCode") in (401, 403) or body.get("code") in (100, 101, 102, 401):
                self._token = await cosa_login(self._session, self._email, self._password)
                resp = await self._rpc(
                    "post", "/api/endpoints/sendACState",
                    {"type": field, "value": value, "endpoint": ep_id},
                )
                body = resp.get("body") or {}
            if body.get("ok") != 1:
                raise RuntimeError(f"sendACState({field}={value}) basarisiz: {resp}")
