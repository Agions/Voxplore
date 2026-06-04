# ADR-005: F5-TTS 本地零样本 vs 云端 TTS

- **状态**: ✅ Accepted
- **日期**: 2026-06-04
- **作者**: 架构团队
- **关联版本**: v1.0.0 ~ v2.0.0

## 背景

配音合成是 SceneFab 核心能力之一。候选方案：

1. **F5-TTS**（本地零样本克隆）
2. **云端 TTS**（Edge-TTS / OpenAI TTS / ElevenLabs）
3. **混合方案**（双引擎切换）

## 决策

采用 **双引擎切换**：
- **Edge-TTS**（云端免费）— 默认引擎，开箱即用
- **F5-TTS**（本地零样本）— 高阶引擎，支持创作者音色克隆

## 对比

| 维度 | Edge-TTS | F5-TTS | 云端商用（ElevenLabs） |
|------|:---:|:---:|:---:|
| **音色数量** | 400+ | 无限（任意参考音频） | 100+ |
| **克隆能力** | ❌ | ✅ 零样本 | ✅ 商用 |
| **音质** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **延迟** | 实时 | 离线 2-3s/句 | 实时 |
| **费用** | 免费 | 免费 | $5-22/月 |
| **隐私** | 云端处理 | 完全本地 | 云端处理 |
| **离线可用** | ❌ | ✅ | ❌ |
| **GPU 加速** | N/A | ✅（可检测 CUDA） | N/A |

## 关键理由

### 1. 双引擎覆盖 95%+ 用户场景
- **入门用户**：Edge-TTS 400+ 音色，无需 GPU
- **进阶用户**：F5-TTS 克隆个人 IP，建立声音品牌

### 2. IP 壁垒
- 创作者克隆自己的声音 → 跨作品统一品牌
- 防止被恶意 AI 模仿（声音作为"个人签名"）

### 3. 完全本地（隐私）
- 创作者声音 = 数字资产，不上传云端
- F5-TTS 零样本可商用（F5-TTS Apache 2.0）

### 4. 性能与成本平衡
- 短句 Edge-TTS 实时生成
- 长篇 F5-TTS 离线批处理
- 用户按需切换

## 实施

### 1. TTS 抽象层（`src/scenefab/services/ai/tts/`）

```python
class BaseTTSAdapter(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: str, **kwargs) -> TTSResult:
        ...

class EdgeTTSAdapter(BaseTTSAdapter):
    """云端免费引擎"""
    ...

class F5TTSAdapter(BaseTTSAdapter):
    """本地零样本引擎"""
    ...
```

### 2. 引擎选择策略

```python
# TTSConfig 决定引擎
@dataclass
class TTSConfig:
    engine: Literal["edge", "f5"] = "edge"
    voice: str = "zh-CN-XiaoxiaoNeural"  # edge 风格
    reference_audio: Optional[Path] = None  # f5 风格
    speed: float = 1.0
    pitch: float = 0.0
```

### 3. 增量缓存（v2.0 P2）

- TTS 缓存按 `text_hash` 索引
- 修改单句只重新合成该句
- 整体音频流式拼接

## 后果

- ✅ 入门用户零配置（默认 Edge-TTS）
- ✅ 进阶用户零样本克隆（F5-TTS）
- ✅ 隐私可控（F5-TTS 模式）
- ⚠️ F5-TTS 需 GPU 加速（CPU 模式慢 5-10x）
- ⚠️ 双引擎维护成本

## 替代方案探索

- **仅 Edge-TTS**: 拒绝（无法建立 IP 壁垒）
- **仅 F5-TTS**: 拒绝（入门门槛高）
- **仅 ElevenLabs**: 拒绝（成本 + 隐私）

## 评审

- 决策贯穿 v1.0 ~ v2.0，已稳定
- 增量缓存优化见 v2.0 改造计划 § 步骤 11
