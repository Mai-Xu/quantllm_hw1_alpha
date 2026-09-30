---
tags: [entity, rpc, zmq]
created: 2026-09-24
updated: 2026-09-24
sources: [raw/vnpy/vnpy/rpc]
---

# 实体：rpc — ZeroMQ 远程调用

`raw/vnpy/vnpy/rpc/`（client/server/common），**不依赖 trader** 的通用 RPC 件；生产对接在独立包 `vnpy_rpcservice`（把 MainEngine 方法 register 成远程 API）。

## 双通道模式
| 通道 | 用途 |
|---|---|
| REQ/REP | 请求-响应远程调用 |
| PUB/SUB | 服务端单向推送 topic（行情/事件/心跳） |

## 调用模型
- **客户端透明代理**（`client.py:55-86`）：`RpcClient.__getattr__` 把任意属性访问变成 `dorpc(*args, **kwargs)`
  - 请求包 `[name, args, kwargs]`；特殊 kwarg `timeout` 默认 30s
  - 响应包 `[True, result]` / `[False, traceback]` → 失败抛 `RemoteException`
- **服务端**：`register(func)` 按 `func.__name__` 入表；`run` 线程 `poll(1000)` 处理请求并捕获异常回传 traceback

## 序列化与线程
- 全程 `send_pyobj/recv_pyobj` = **pickle**——任意 Python 对象直传，**仅限可信内网**，跨语言不可用
- `RpcServer.start` bind 双 socket 后起工作线程；`publish` 带锁与 REP 循环共享
- **心跳**：服务端每 10s PUB `"heartbeat"`；客户端 SUB 30s 超时触发 `on_disconnected`
- `common.py` 设 `SIGINT=SIG_DFL` 让 Ctrl-C 能中断阻塞 recv

## 与交易系统关系
把「远程进程里的策略/监控」接到本地 MainEngine 的桥梁；事件驱动见 [[event-driven-architecture]]。GUI/实盘链路本身不经过 rpc。

## 相关页面
[[main-engine]] · [[event-engine]] · [[vnpy-source]]
