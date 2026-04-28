# Source Metadata
- protocol: sut
- kind: private-spec
- source_file: sut_spec.md
- source_url: internal://campus-bike/sut/v1

# SUT: Smart Unlock Transport

SUT（Smart Unlock Transport）是一个用于校园内遥控共享单车的私有控制协议。它服务于校园单车调度平台、宿舍区停车点、教学楼电子围栏和学生端小程序之间的通信。

SUT 的目标不是做一个通用互联网协议，而是为“校园内、低速移动、设备数量多、交互很具体”的共享单车场景提供可控、可解释、便于演示的控制能力。

SUT 默认运行在校园边缘网关与车辆锁控模块之间，默认控制端口为 `9750`。

它最有特点的地方在于：

- 支持远程开锁与临时控速
- 支持“晚高峰排队延时”与“宿舍区限流抖动”
- 支持电子围栏内外的不同行为策略
- 支持“老师优先车位”和“考试周静音解锁”等校园特性
- 响应中可回显详细诊断字段，适合教学展示与 RAG 问答

# 1. Introduction

在校园共享单车场景中，问题并不只是“能不能开锁”，而是：

- 某个用户是否有资格解锁
- 当前车是否在允许骑行的区域内
- 是否处于宿舍楼夜间静默时段
- 是否需要对开锁行为附加人工延时，避免同一停车点瞬时拥塞
- 是否需要在教学楼周边对车辆施加限速策略

SUT 就是围绕这些具体问题设计的。它将“身份校验、位置策略、锁控动作、延时控制、回显诊断”统一到一个轻量协议里。

一次最小的 SUT 事务通常包括：

1. 学生端发起 `UNLOCK` 请求
2. 网关校验用户身份、车辆状态与地理围栏
3. 策略引擎决定是否立即开锁、延时开锁或拒绝开锁
4. 锁控模块执行动作并返回诊断结果

# 2. Campus-Specific Features

SUT 并不是抽象的实验协议，它内建了很多“校园里才会出现”的有趣特性。

## 2.1 Unlock Delay Window

客户端可通过 `Desired-Unlock-Latency` 字段声明期望的附加开锁延时，单位为毫秒。这个机制主要用于演示“高峰期停车点排队控制”。

服务器可以：

- 忽略该字段并立即开锁
- 接受该字段并延迟开锁
- 对超限请求进行裁剪

标准允许范围为 `0ms` 到 `1800ms`。

例如：

- 普通教学区默认允许 `0ms` 到 `600ms`
- 宿舍楼下晚高峰允许 `200ms` 到 `1800ms`
- 图书馆门口静音区建议 `300ms` 到 `900ms`

## 2.2 Crowd Jitter

SUT 支持 `Crowd-Jitter-Mode`，用于模拟“同一停车点多人同时扫码”的不稳定排队效果。

可选值如下：

- `off`：无抖动
- `soft`：增加 `10ms` 到 `80ms` 抖动
- `rush`：增加 `80ms` 到 `300ms` 抖动
- `festival`：增加 `300ms` 到 `900ms` 抖动

其中：

- `rush` 用于上课前 10 分钟的教学楼停车点
- `festival` 用于迎新日、社团招新夜、市集活动等特殊场景

`festival` 模式只允许在演示环境或校园活动日策略中启用。

## 2.3 Quiet Unlock Mode

如果请求头中包含 `Quiet-Unlock: yes`，锁控模块在开锁时应使用低提示音模式，避免在宿舍区夜间产生连续尖锐提示声。

这个特性很适合演示，因为它体现了“协议不是只管网络，也在管真实校园生活中的细节体验”。

## 2.4 Teacher Priority Bay

SUT 支持 `Bay-Priority` 字段，用于控制是否允许车辆进入“教师优先停车点”。

规则如下：

- 普通学生请求不得将车预约到教师优先停车点
- 教职工卡绑定账户可使用 `faculty` 优先级
- 调度员账户可使用 `ops` 优先级

## 2.5 Exam Week Slow Zone

在考试周期间，教学楼周边可启用 `Exam-Slow-Zone` 策略。进入该区域的车辆即使已成功解锁，也可能被远程下发限速参数。

这样可以让 SUT 同时支持：

- 解锁控制
n- 区域限速
- 特殊时段校园管理

# 3. Transaction Model

每个 SUT 事务围绕“一辆车的一次控制动作”展开。一个事务包含以下阶段：

1. `Receive`
2. `Authenticate`
3. `Locate`
4. `Policy`
5. `Delay`
6. `Actuate`
7. `Acknowledge`

其含义如下：

- `Receive`：接收请求
- `Authenticate`：校验用户身份、学生证状态或教工权限
- `Locate`：读取车辆位置和停车点信息
- `Policy`：匹配围栏、时段和校园活动策略
- `Delay`：应用延时与抖动
- `Actuate`：执行开锁、鸣笛、限速或取消动作
- `Acknowledge`：返回结果与诊断字段

# 4. Header Fields

SUT 请求头至少应包含以下字段：

## 4.1 Version

协议版本。当前固定为 `1`。

## 4.2 Request-ID

请求唯一标识。服务器必须用它进行幂等检测和重试识别。

如果两个请求具有相同 `Request-ID`：

- 若目标车辆与动作参数完全一致，可视为安全重试
- 若车辆编号或动作参数不同，必须返回冲突错误

## 4.3 User-ID

发起操作的用户标识。它可以绑定学生、老师或运维调度员身份。

## 4.4 Bike-ID

目标单车编号。每次控制动作必须明确指定一辆单车。

## 4.5 Action

动作类型。当前支持：

- `UNLOCK`
- `LOCK`
- `PING`
- `LIMIT_SPEED`
- `RING`
- `RESERVE_BAY`

## 4.6 Desired-Unlock-Latency

客户端请求的附加开锁延时，单位为毫秒。通常用于校园演示模式、高峰排队控制或停车点分流。

## 4.7 Crowd-Jitter-Mode

请求希望采用的人群抖动模式：

- `off`
- `soft`
- `rush`
- `festival`

## 4.8 Quiet-Unlock

是否启用静音开锁：

- `yes`
- `no`

## 4.9 Geo-Fence

当前目标区域标识，例如：

- `dorm-east`
- `library-north`
- `teaching-a`
- `gym-square`

## 4.10 Trace-Echo

是否要求服务器回显详细诊断数据：

- `yes`
- `no`

# 5. Request Types

## 5.1 UNLOCK

请求远程开锁。它是 SUT 中最核心的请求类型。

服务器在处理 `UNLOCK` 时必须至少检查：

- 用户是否具有可用骑行资格
- 单车电量是否高于最低阈值
- 车辆是否停在允许出发的区域
- 当前是否触发宿舍区静音策略
- 当前停车点是否处于高峰排队期

## 5.2 LOCK

请求远程关锁。通常用于用户结束骑行后异常补锁，或调度员远程收车。

## 5.3 PING

查询车辆在线状态、锁控模块健康状态和最近一次动作时间。

## 5.4 LIMIT_SPEED

下发限速动作。常用于考试周慢行区、操场周边、校医院附近或下坡风险路段。

## 5.5 RING

远程鸣笛，通常用于帮助用户在密集停车区快速找到自己的车。

但在 `Quiet-Unlock` 区域或夜间宿舍区，`RING` 可能被拒绝。

## 5.6 RESERVE_BAY

预约停车点。该请求可用于引导车辆停入指定区域，例如“图书馆北门临停区”或“教师优先停车点”。

# 6. Response Codes

## 6.1 200 OK

请求已成功执行。

## 6.2 202 DELAYED_UNLOCK

请求已通过校验，但当前正处于延时开锁阶段。

## 6.3 208 SAFE_RETRY_ACCEPTED

服务器检测到相同 `Request-ID` 的重复请求，且动作一致，因此将其视为安全重试。

## 6.4 409 REQUEST_CONFLICT

服务器发现相同 `Request-ID` 对应了不同车辆或不同动作参数。

## 6.5 423 BIKE_ALREADY_UNLOCKED

目标车辆已经处于开锁状态。

## 6.6 452 GEO_FENCE_DENIED

目标车辆位于禁止远程控制的区域，或用户无权在当前围栏内执行请求。

## 6.7 463 LATENCY_LIMIT_APPLIED

请求的开锁延时超过当前校园策略允许范围，服务器已自动裁剪。

## 6.8 475 QUIET_HOURS_RESTRICTED

当前处于宿舍楼夜间静默时段，不允许高提示音鸣笛或强提示开锁。

## 6.9 503 JITTER_POLICY_REJECTED

请求使用了当前环境不允许的抖动模式，例如在正常教学日请求 `festival`。

# 7. Timing and Delay Rules

SUT 明确区分三种时间：

- 用户请求的延时
- 策略引擎附加的排队延时
- 最终实际执行延时

## 7.1 Effective Unlock Delay

最终开锁延时按以下步骤确定：

1. 读取 `Desired-Unlock-Latency`
2. 结合当前围栏策略应用上限
3. 根据 `Crowd-Jitter-Mode` 增加抖动
4. 生成 `Effective-Unlock-Delay`

例如：

- `Desired-Unlock-Latency = 500ms`
- 区域 = `teaching-a`
- `Crowd-Jitter-Mode = rush`
- 实际附加抖动 = `120ms`
- 则 `Effective-Unlock-Delay = 620ms`

## 7.2 Quiet Hours

在 `22:30` 到 `06:30` 的宿舍区静默时间段内：

- `RING` 可能被拒绝
- `UNLOCK` 可以执行，但应尽量采用静音模式
- 若客户端未设置 `Quiet-Unlock: yes`，服务器可自动改写为静音策略

## 7.3 Festival Day Policy

在校园活动日，如果停车点人流密集，策略引擎可临时启用：

- 更高的延时上限
- `festival` 抖动模式
- 更严格的围栏停放约束

这个特性很适合问答系统展示“协议不仅有字段，还有情境化策略”。

# 8. Example Transaction

下面给出一个典型的开锁请求：

```text
UNLOCK /bike SUT/1
Version: 1
Request-ID: bike-20260422-0815
User-ID: stu-20231234
Bike-ID: BK-7A-221
Action: UNLOCK
Desired-Unlock-Latency: 700
Crowd-Jitter-Mode: rush
Quiet-Unlock: yes
Geo-Fence: dorm-east
Trace-Echo: yes
```

一个可能的响应如下：

```text
SUT/1 200 OK
Request-ID: bike-20260422-0815
Bike-ID: BK-7A-221
Auth-Time: 18ms
Locate-Time: 23ms
Policy-Time: 12ms
Applied-Jitter: 146ms
Effective-Unlock-Delay: 846ms
Actuate-Time: 31ms
Fence-Policy: dorm-quiet-hour
```

如果客户端请求了过大的延时，也可能收到：

```text
SUT/1 463 LATENCY_LIMIT_APPLIED
Request-ID: bike-20260422-0819
Requested-Latency: 2600ms
Applied-Latency: 1800ms
Applied-Jitter: 0ms
```

如果在宿舍夜间请求高提示音鸣笛，可能收到：

```text
SUT/1 475 QUIET_HOURS_RESTRICTED
Request-ID: bike-20260422-0901
Action: RING
Geo-Fence: dorm-east
Policy: night-quiet-rule
```

# 9. Reliability Rules

SUT 必须支持以下可靠性规则：

- 相同 `Request-ID` 且参数一致的请求视为安全重试
- 相同 `Request-ID` 但不同 `Bike-ID` 的请求视为冲突
- `PING` 请求不得改变车辆状态
- `LIMIT_SPEED` 请求必须记录策略来源
- `UNLOCK` 成功前不得提前返回 `200 OK`
- `RESERVE_BAY` 不应覆盖教师优先停车点的本地规则

# 10. Security Considerations

虽然 SUT 主要用于校园内网，但仍需满足以下安全要求：

- 每个 `User-ID` 必须绑定真实身份类别
- 每个控制请求必须记录 `Bike-ID`、围栏与动作类型
- 运维账户与普通学生账户必须区分权限
- 教师优先停车点不可被学生账户伪造预约
- `Trace-Echo` 不应泄露内部节点 IP 或运维拓扑
- 夜间静默规则不得被客户端单方面绕过

# 11. Why SUT Is Memorable

SUT 之所以适合作为一个“有趣又特点明显”的私有协议，是因为它不是普通的上传协议或聊天协议，而是一个很具体的校园单车控制协议。

它有很多容易记住、也容易提问的点：

- 它能远程开锁共享单车
- 它支持宿舍区夜间静音开锁
- 它支持考试周慢行区限速
- 它支持教学楼高峰期排队延时
- 它还有 `festival` 抖动模式来模拟活动日人流拥挤

例如可以问：

- `SUT 为什么需要 Quiet-Unlock？`
- `festival 模式和 rush 模式的区别是什么？`
- `什么情况下会返回 475 QUIET_HOURS_RESTRICTED？`
- `SUT 如何区分安全重试和请求冲突？`
- `为什么考试周可以通过 SUT 下发限速？`
