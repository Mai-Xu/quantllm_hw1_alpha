"""
离线测试：不连网络、不下单，只验证归属过滤、终态校验与配置读取的 fail-closed 行为。

运行：
    python tests/test_offline.py          # 直接运行（打印 PASS/FAIL）
    pytest tests/test_offline.py -v       # 或在 pytest 下运行

覆盖点（对应评审反馈）：
  A. 委托归属：FrontID + SessionID + OrderRef 三段匹配
  B. 成交归属收紧：OrderRef 登记 + OrderSysID 自洽 + 方向一致（拒收他会话成交）
  C. 终态校验：平仓成交 + 持仓归零 + 无活动委托，任一不满足即 FAIL
  D. 脱敏：mask 不泄漏原值
  E. 配置缺失 fail-closed：缺 userid/password 时退出码 2
"""

import os
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEMO_DIR))

# 导入前先给出假凭据（load_setting 只校验存在性，不联网）
os.environ.setdefault("Mai_SimNow_userid", "TEST0001")
os.environ.setdefault("Mai_SimNow_password", "dummy-not-a-real-secret")

import demo  # noqa: E402


def _td(sessionid: int = 111, frontid: int = 1) -> "demo.VerifiedTdApi":
    """构造一个已登录、已登记 OrderRef=1(open)/2(close) 的交易对象。"""
    td = demo.VerifiedTdApi()
    td.frontid = frontid
    td.sessionid = sessionid
    for ref, tag, direction in ((1, "open", "0"), (2, "close", "1")):
        td.my_order_refs.add(ref)
        td.ref_meta[ref] = {"tag": tag, "direction": direction,
                            "offset": "0" if tag == "open" else "3",
                            "volume": 1, "price": 900.0}
        td.status[ref] = "0"
        td.traded_volume[ref] = 1
        td.trade_volume[ref] = 1
    return td


# ---------------------------------------------------------------- A. 委托归属

def test_order_is_mine_accepts_own_session():
    td = _td()
    d = {"FrontID": 1, "SessionID": 111, "OrderRef": "1"}
    assert td.order_is_mine(d) is True


def test_order_is_mine_rejects_other_session():
    td = _td(sessionid=111)
    d = {"FrontID": 1, "SessionID": 999, "OrderRef": "1"}     # 别的前置会话
    assert td.order_is_mine(d) is False


def test_order_is_mine_rejects_unregistered_ref():
    td = _td()
    d = {"FrontID": 1, "SessionID": 111, "OrderRef": "77"}    # 本会话但非我登记
    assert td.order_is_mine(d) is False


# ---------------------------------------------------------------- B. 成交归属

def test_trade_ref_accepts_registered_ref_without_sysid():
    td = _td()
    d = {"OrderRef": "1", "Direction": "0", "OrderSysID": ""}
    assert td.trade_ref(d) == 1


def test_trade_ref_accepts_matching_sysid():
    td = _td()
    td.sysid_to_ref["SYS-A"] = 1
    d = {"OrderRef": "1", "Direction": "0", "OrderSysID": "SYS-A"}
    assert td.trade_ref(d) == 1


def test_trade_ref_rejects_unregistered_ref():
    td = _td()
    d = {"OrderRef": "55", "Direction": "0", "OrderSysID": ""}
    assert td.trade_ref(d) is None


def test_trade_ref_rejects_foreign_sysid():
    """收紧点：带系统号但该号未由本会话登记 → 拒收（多会话并行时的关键防线）。"""
    td = _td()
    d = {"OrderRef": "1", "Direction": "0", "OrderSysID": "SYS-OTHER"}
    assert td.trade_ref(d) is None


def test_trade_ref_rejects_inconsistent_sysid():
    """系统号登记在另一单 → 不自洽，拒收。"""
    td = _td()
    td.sysid_to_ref["SYS-B"] = 2            # 该号属于 close 单
    d = {"OrderRef": "1", "Direction": "0", "OrderSysID": "SYS-B"}
    assert td.trade_ref(d) is None


def test_trade_ref_rejects_direction_mismatch():
    td = _td()
    d = {"OrderRef": "1", "Direction": "1", "OrderSysID": ""}   # 1 号是买单
    assert td.trade_ref(d) is None


# ---------------------------------------------------------------- C. 终态校验

def test_verify_flat_passes_when_closed_flat_and_idle():
    td = _td()
    td.position_rows = []
    td.position_queried = True
    ok, reason = td.verify_flat()
    assert ok is True, reason


def test_verify_flat_fails_when_close_not_filled():
    td = _td()
    td.trade_volume[2] = 0                  # 平仓未成交
    td.position_queried = True
    ok, reason = td.verify_flat()
    assert ok is False and "平仓未全部成交" in reason


def test_verify_flat_fails_when_position_not_queried():
    td = _td()
    td.position_queried = False
    ok, reason = td.verify_flat()
    assert ok is False and "无法证明空仓" in reason


def test_verify_flat_fails_when_position_nonzero():
    td = _td()
    td.position_rows = [{"instrument": demo.SYMBOL, "direction": "2",
                         "position": 1, "yd": 0, "today": 1}]
    td.position_queried = True
    ok, reason = td.verify_flat()
    assert ok is False and "未归零" in reason


def test_verify_flat_fails_when_active_order_exists():
    td = _td()
    td.position_rows = []
    td.position_queried = True
    td.status[2] = "3"                      # 平仓单仍挂在场内
    ok, reason = td.verify_flat()
    assert ok is False and "活动委托" in reason


def test_active_orders_ignores_terminal_status():
    td = _td()
    td.status[1] = "0"                      # 全成
    td.status[2] = "5"                      # 已撤
    assert td.active_orders() == []


# ---------------------------------------------------------------- D. 脱敏

def test_mask_hides_value():
    assert demo.mask("<INVESTOR_ID>") == "******"
    assert "<INVESTOR_ID>" not in demo.mask("<INVESTOR_ID>")
    assert demo.mask("") == ""


# ---------------------------------------------------------------- E. fail-closed

def test_config_missing_exits_with_code_2():
    """
    缺配置时必须以退出码 2 终止（fail-closed）。

    用子进程隔离：demo 模块在导入时即校验配置并以 sys.exit(2) 退出，
    在本进程内 reload 会连带杀死测试进程，故走 subprocess。

    Windows 注意：os.environ 的键会被规范化为大写，剔除凭据时必须按大写比较，
    否则过滤形同虚设（本测试曾因此误判）。
    """
    import subprocess
    exclude = {"MAI_SIMNOW_USERID", "MAI_SIMNOW_PASSWORD", "MAI_SIMNOW_PASSWARD"}
    env = {k: v for k, v in os.environ.items() if k.upper() not in exclude}
    env["PYTHONIOENCODING"] = "utf-8"
    code = (
        "import os, sys;"
        "sys.path.insert(0, r'%s');"
        "print('CHILD_ENV_HAS_USERID', 'MAI_SIMNOW_USERID' in {k.upper() for k in os.environ});"
        "import demo; print('IMPORT_OK')" % DEMO_DIR
    )
    proc = subprocess.run([sys.executable, "-c", code], env=env,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)
    detail = f"rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    assert proc.returncode == 2, f"期望退出码 2，实际：\n{detail}"
    assert "IMPORT_OK" not in proc.stdout, f"缺配置时不应完成导入：\n{detail}"
    assert "缺少必需的环境变量" in (proc.stdout + proc.stderr), detail


def _run_all() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
