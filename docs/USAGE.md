# MoltsPay Python SDK 使用文档

## 安装

```bash
pip install moltspay
```

## 快速开始

### 1. 初始化客户端

```python
from moltspay import MoltsPay

# 自动创建钱包（首次运行）或加载已有钱包
client = MoltsPay()

print(f"钱包地址: {client.address}")
# 钱包保存在 ~/.moltspay/wallet.json
```

### 2. 发现可用服务

```python
# 查看服务提供商有什么服务
services = client.discover("https://juai8.com/zen7")

for svc in services:
    print(f"- {svc.id}: {svc.price} {svc.currency}")
    # - text-to-video: 0.99 USDC
    # - image-to-video: 1.49 USDC
```

### 3. 支付并调用服务

```python
# 支付并调用服务
result = client.pay(
    "https://juai8.com/zen7",    # 服务地址
    "text-to-video",             # 服务 ID
    prompt="一只猫在沙滩上跳舞"    # 服务参数
)

if result.success:
    print(f"视频链接: {result.result['video_url']}")
else:
    print(f"失败: {result.error}")
```

---

## 钱包管理

### 钱包文件位置

默认: `~/.moltspay/wallet.json`

```python
# 使用自定义路径
client = MoltsPay(wallet_path="~/my-agent/wallet.json")
```

### 钱包文件格式

与 Node.js CLI 完全兼容：

```json
{
  "address": "0x...",
  "privateKey": "0x...",
  "chain": "base",
  "encrypted": false,
  "limits": {
    "maxPerTx": 10,
    "maxPerDay": 100
  },
  "spending": {
    "today": "2026-03-06",
    "amount": 5.5
  }
}
```

### 从私钥初始化

```python
# 直接使用私钥（不保存文件）
client = MoltsPay(private_key="0x...")
```

---

## 消费限额

### 查看限额

```python
limits = client.limits()

print(f"单笔限额: {limits.max_per_tx} USDC")
print(f"每日限额: {limits.max_per_day} USDC")
print(f"今日已消费: {limits.spent_today} USDC")
print(f"今日剩余: {limits.remaining_daily} USDC")
```

### 设置限额

```python
# 设置单笔最高 20 USDC，每日最高 200 USDC
client.set_limits(max_per_tx=20, max_per_day=200)
```

### 限额保护

超出限额时会自动拒绝：

```python
from moltspay import MoltsPay, LimitExceeded

client = MoltsPay()
client.set_limits(max_per_tx=5)

try:
    result = client.pay(...)  # 假设服务要 10 USDC
except LimitExceeded as e:
    print(f"超出{e.limit_type}限额: {e.amount} > {e.limit}")
```

---

## 异步支持

```python
import asyncio
from moltspay import AsyncMoltsPay

async def main():
    async with AsyncMoltsPay() as client:
        # 发现服务
        services = await client.discover("https://juai8.com/zen7")
        
        # 支付调用
        result = await client.pay(
            "https://juai8.com/zen7",
            "text-to-video",
            prompt="a dragon flying"
        )
        print(result.result)

asyncio.run(main())
```

---

## 错误处理

```python
from moltspay import (
    MoltsPay,
    PaymentError,
    InsufficientFunds,
    LimitExceeded,
    WalletError,
)

client = MoltsPay()

try:
    result = client.pay(...)
    
except InsufficientFunds as e:
    # 余额不足
    print(f"余额不足: 需要 {e.required}，只有 {e.balance}")
    
except LimitExceeded as e:
    # 超出限额
    print(f"超出限额: {e.limit_type} = {e.limit}")
    
except PaymentError as e:
    # 支付失败
    print(f"支付失败: {e}")
    if e.tx_hash:
        print(f"交易哈希: {e.tx_hash}")
        
except WalletError as e:
    # 钱包错误
    print(f"钱包错误: {e}")
```

---

## 与 Node.js CLI 互操作

### 场景 1: 先用 Node.js 创建钱包

```bash
# Node.js CLI
npx moltspay init --chain base
npx moltspay config --max-per-tx 10 --max-per-day 100
```

```python
# Python 直接使用同一个钱包
from moltspay import MoltsPay

client = MoltsPay()  # 自动加载 ~/.moltspay/wallet.json
print(client.address)  # 与 Node.js 相同的地址
```

### 场景 2: 纯 Python 使用

```python
from moltspay import MoltsPay

# 首次运行自动创建钱包
client = MoltsPay()
client.set_limits(max_per_tx=10, max_per_day=100)

# 之后 Node.js CLI 也能用这个钱包
# npx moltspay status  # 会显示同样的地址和限额
```

---

## 支持的区块链

| 链 | Chain ID | 状态 |
|---|----------|------|
| Base Mainnet | 8453 | ✅ 默认 |
| Base Sepolia | 84532 | ✅ 测试网 |

```python
# 使用测试网
client = MoltsPay(chain="base_sepolia")
```

---

## 完整示例: AI Agent 集成

```python
"""
示例: 在你的 AI Agent 中集成 MoltsPay
"""
from moltspay import MoltsPay, LimitExceeded, PaymentError

class MyAgent:
    def __init__(self):
        self.moltspay = MoltsPay()
        self.moltspay.set_limits(max_per_tx=5, max_per_day=50)
    
    def generate_video(self, prompt: str) -> str:
        """调用 Zen7 视频生成服务"""
        try:
            result = self.moltspay.pay(
                "https://juai8.com/zen7",
                "text-to-video",
                prompt=prompt
            )
            
            if result.success:
                return result.result["video_url"]
            else:
                return f"生成失败: {result.error}"
                
        except LimitExceeded as e:
            return f"超出消费限额，请联系管理员"
            
        except PaymentError as e:
            return f"支付失败: {e}"
    
    def check_budget(self) -> dict:
        """检查今日预算"""
        limits = self.moltspay.limits
        return {
            "spent": limits.spent_today,
            "remaining": limits.remaining_daily,
            "max_daily": limits.max_per_day,
        }


# 使用
agent = MyAgent()
video_url = agent.generate_video("一只猫在弹钢琴")
print(video_url)

budget = agent.check_budget()
print(f"今日已消费: ${budget['spent']}, 剩余: ${budget['remaining']}")
```

---

## API 参考

### MoltsPay

| 方法 | 描述 |
|------|------|
| `MoltsPay(wallet_path=None, private_key=None, chain="base")` | 初始化客户端 |
| `.address` | 钱包地址 |
| `.discover(service_url)` | 发现可用服务 |
| `.pay(service_url, service_id, **params)` | 支付并调用服务 |
| `.limits()` | 获取消费限额 |
| `.set_limits(max_per_tx, max_per_day)` | 设置消费限额 |
| `.balance()` | 获取余额 (TODO) |

### PaymentResult

| 字段 | 类型 | 描述 |
|------|------|------|
| `success` | bool | 是否成功 |
| `amount` | float | 支付金额 |
| `service_id` | str | 服务 ID |
| `result` | Any | 服务返回结果 |
| `error` | str | 错误信息 |
| `tx_hash` | str | 交易哈希 |

### Limits

| 字段 | 类型 | 描述 |
|------|------|------|
| `max_per_tx` | float | 单笔限额 |
| `max_per_day` | float | 每日限额 |
| `spent_today` | float | 今日已消费 |
| `remaining_daily` | float | 今日剩余 |

---

## 链接

- **MoltsPay 官网**: https://moltspay.com
- **Node.js SDK**: https://npmjs.com/package/moltspay
- **GitHub**: https://github.com/Yaqing2023/moltspay-python
- **示例服务 (Zen7)**: https://juai8.com/zen7/services
