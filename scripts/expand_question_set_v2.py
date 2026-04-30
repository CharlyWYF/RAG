from __future__ import annotations

import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTION_SET_DIR = PROJECT_ROOT / "docs" / "test_question_set"
JSON_PATH = QUESTION_SET_DIR / "test_question_set.json"
CSV_PATH = QUESTION_SET_DIR / "test_question_set.csv"
MD_PATH = QUESTION_SET_DIR / "test_question_set.md"


NEW_QUESTIONS = [
    {"id": 31, "question": "DNSKEY、RRSIG、DS、NSEC 在 DNSSEC 中分别承担什么作用？", "protocol_group": "DNS", "question_type": "字段类", "target_document": "RFC 4034", "difficulty": "中等", "expected_keypoints": "区分各资源记录职责", "should_refuse": False, "section": "rfc_questions"},
    {"id": 32, "question": "RFC 4035 中安全感知解析器需要做哪些额外工作？", "protocol_group": "DNS", "question_type": "机制类", "target_document": "RFC 4035", "difficulty": "较难", "expected_keypoints": "验证签名、处理安全状态、认证响应", "should_refuse": False, "section": "rfc_questions"},
    {"id": 33, "question": "DNS 的层次化命名空间为什么适合大规模网络？", "protocol_group": "DNS", "question_type": "机制类", "target_document": "RFC 1034", "difficulty": "中等", "expected_keypoints": "分布式管理、可扩展、组织结构映射", "should_refuse": False, "section": "rfc_questions"},
    {"id": 34, "question": "HTTP 语义和 HTTP/1.1 消息语法为什么被拆成不同 RFC？", "protocol_group": "HTTP", "question_type": "综合类", "target_document": "RFC 9110 / RFC 9112", "difficulty": "较难", "expected_keypoints": "语义与承载分离", "should_refuse": False, "section": "rfc_questions"},
    {"id": 35, "question": "HTTP/3 为什么要建立在 QUIC 之上而不是 TCP 之上？", "protocol_group": "HTTP", "question_type": "机制类", "target_document": "RFC 9114", "difficulty": "中等", "expected_keypoints": "QUIC 提供不同传输特性", "should_refuse": False, "section": "rfc_questions"},
    {"id": 36, "question": "HTTP/2 中多路复用为什么能改善应用性能？", "protocol_group": "HTTP", "question_type": "机制类", "target_document": "RFC 7540 / RFC 9113", "difficulty": "中等", "expected_keypoints": "并发请求、减少 HOL 阻塞等", "should_refuse": False, "section": "rfc_questions"},
    {"id": 37, "question": "RFC 6066 中哪些 TLS 扩展最值得注意？", "protocol_group": "TLS", "question_type": "字段类", "target_document": "RFC 6066", "difficulty": "中等", "expected_keypoints": "典型扩展，如 server_name 等", "should_refuse": False, "section": "rfc_questions"},
    {"id": 38, "question": "RFC 7301 中客户端和服务端如何完成 ALPN 协商？", "protocol_group": "TLS", "question_type": "流程类", "target_document": "RFC 7301", "difficulty": "中等", "expected_keypoints": "ClientHello / ServerHello 中的协商过程", "should_refuse": False, "section": "rfc_questions"},
    {"id": 39, "question": "RFC 5280 中证书路径验证主要解决什么问题？", "protocol_group": "TLS", "question_type": "机制类", "target_document": "RFC 5280", "difficulty": "中等", "expected_keypoints": "路径验证、信任链判断", "should_refuse": False, "section": "rfc_questions"},
    {"id": 40, "question": "RFC 8446 中 TLS 1.3 相比 TLS 1.2 的握手流程有哪些主要变化？", "protocol_group": "TLS", "question_type": "对比类", "target_document": "RFC 8446 / RFC 5246", "difficulty": "较难", "expected_keypoints": "更少往返、结构简化等", "should_refuse": False, "section": "rfc_questions"},
    {"id": 41, "question": "RFC 793 与 RFC 9293 在 TCP 规范角色上有什么关系？", "protocol_group": "TCP", "question_type": "对比类", "target_document": "RFC 793 / RFC 9293", "difficulty": "中等", "expected_keypoints": "旧版与整合更新版关系", "should_refuse": False, "section": "rfc_questions"},
    {"id": 42, "question": "TCP 为什么需要可靠、按序的字节流服务？", "protocol_group": "TCP", "question_type": "机制类", "target_document": "RFC 793 / RFC 9293", "difficulty": "中等", "expected_keypoints": "服务目标与应用需求", "should_refuse": False, "section": "rfc_questions"},
    {"id": 43, "question": "UDP 为什么常被用于简单请求-响应或轻量传输场景？", "protocol_group": "UDP", "question_type": "机制类", "target_document": "RFC 768", "difficulty": "中等", "expected_keypoints": "轻量、无连接、低开销", "should_refuse": False, "section": "rfc_questions"},
    {"id": 44, "question": "IPv6 中 Path MTU Discovery 为什么重要？", "protocol_group": "IP", "question_type": "机制类", "target_document": "RFC 8201 / RFC 8200", "difficulty": "中等", "expected_keypoints": "避免分片与路径限制", "should_refuse": False, "section": "rfc_questions"},
    {"id": 45, "question": "RFC 1122 在整个互联网协议栈中的定位是什么？", "protocol_group": "IP", "question_type": "定义类", "target_document": "RFC 1122", "difficulty": "中等", "expected_keypoints": "主机实现要求文档", "should_refuse": False, "section": "rfc_questions"},
    {"id": 46, "question": "ICMP 为什么被认为是 IP 的组成部分而不是普通上层协议？", "protocol_group": "ICMP", "question_type": "机制类", "target_document": "RFC 792", "difficulty": "中等", "expected_keypoints": "错误控制与网络控制作用", "should_refuse": False, "section": "rfc_questions"},
    {"id": 47, "question": "ARP 为什么在局域网通信中不可缺少？", "protocol_group": "ARP", "question_type": "机制类", "target_document": "RFC 826", "difficulty": "简单", "expected_keypoints": "地址解析对链路通信必要", "should_refuse": False, "section": "rfc_questions"},
    {"id": 48, "question": "HTTP over TLS 和 TLS 本身分别解决什么问题？", "protocol_group": "HTTP/TLS", "question_type": "对比类", "target_document": "RFC 2818 / RFC 8446", "difficulty": "中等", "expected_keypoints": "应用语义 vs 安全通道", "should_refuse": False, "section": "rfc_questions"},
    {"id": 49, "question": "ALPN、HTTP/2 和 HTTPS 三者之间是什么关系？", "protocol_group": "TLS/HTTP", "question_type": "综合类", "target_document": "RFC 7301 / RFC 2818 / RFC 9113", "difficulty": "较难", "expected_keypoints": "协商应用协议与 HTTPS 承载关系", "should_refuse": False, "section": "rfc_questions"},
    {"id": 50, "question": "DNSSEC 与普通 DNS 在“响应可信性”上有什么本质差异？", "protocol_group": "DNS", "question_type": "对比类", "target_document": "RFC 4033 / RFC 4035", "difficulty": "中等", "expected_keypoints": "有无签名验证与认证能力", "should_refuse": False, "section": "rfc_questions"},
    {"id": 51, "question": "HTTP/3 在实际生产环境中一定比 HTTP/2 更快吗？", "protocol_group": "HTTP", "question_type": "证据不足类", "target_document": "RFC 9113 / RFC 9114", "difficulty": "中等", "expected_keypoints": "RFC 可解释机制差异，但不能绝对判断所有真实环境性能", "should_refuse": True, "section": "refusal_questions"},
    {"id": 52, "question": "TLS 1.3 是否在所有场景下都比 TLS 1.2 更安全？", "protocol_group": "TLS", "question_type": "证据不足类", "target_document": "RFC 5246 / RFC 8446", "difficulty": "中等", "expected_keypoints": "RFC 可说明改进，但不应绝对化", "should_refuse": True, "section": "refusal_questions"},
    {"id": 53, "question": "哪种协议在现实网络里性能最好？", "protocol_group": "综合", "question_type": "证据不足类", "target_document": "多 RFC", "difficulty": "简单", "expected_keypoints": "需要具体场景，RFC 不足以直接比较最好", "should_refuse": True, "section": "refusal_questions"},
    {"id": 54, "question": "DNSSEC 是否一定能完全防止所有 DNS 攻击？", "protocol_group": "DNS", "question_type": "证据不足类", "target_document": "RFC 4033 / RFC 4034 / RFC 4035", "difficulty": "中等", "expected_keypoints": "可说明能力边界，但不应绝对化", "should_refuse": True, "section": "refusal_questions"},
    {"id": 55, "question": "QUIC 是否一定会取代 TCP？", "protocol_group": "HTTP/IP", "question_type": "证据不足类", "target_document": "RFC 9114 / RFC 9293", "difficulty": "中等", "expected_keypoints": "RFC 不能支持未来趋势的确定性判断", "should_refuse": True, "section": "refusal_questions"},
    {"id": 56, "question": "HTTP/2 是否在所有移动网络环境下都优于 HTTP/1.1？", "protocol_group": "HTTP", "question_type": "证据不足类", "target_document": "RFC 7540 / RFC 9113", "difficulty": "中等", "expected_keypoints": "RFC 描述机制，不足以断言所有现实环境效果", "should_refuse": True, "section": "refusal_questions"},
    {"id": 57, "question": "IPv6 是否一定比 IPv4 更安全？", "protocol_group": "IP", "question_type": "证据不足类", "target_document": "RFC 791 / RFC 8200", "difficulty": "中等", "expected_keypoints": "RFC 可描述机制差异，但不能绝对判断", "should_refuse": True, "section": "refusal_questions"},
    {"id": 58, "question": "ALPN 是否可以解决所有 HTTPS 协议协商问题？", "protocol_group": "TLS", "question_type": "证据不足类", "target_document": "RFC 7301", "difficulty": "中等", "expected_keypoints": "仅解决应用层协议协商，不应绝对化", "should_refuse": True, "section": "refusal_questions"},
    {"id": 59, "question": "Negative caching 是否一定能提升所有 DNS 场景下的性能？", "protocol_group": "DNS", "question_type": "证据不足类", "target_document": "RFC 2308", "difficulty": "中等", "expected_keypoints": "作用明确，但不应扩展为所有场景都更优", "should_refuse": True, "section": "refusal_questions"},
    {"id": 60, "question": "私有协议一定比标准协议更适合特定场景吗？", "protocol_group": "综合", "question_type": "证据不足类", "target_document": "sut_spec.md / 多 RFC", "difficulty": "中等", "expected_keypoints": "无法依据文档作绝对判断", "should_refuse": True, "section": "refusal_questions"},
    {"id": 61, "question": "SUT 是什么协议？主要用于什么场景？", "protocol_group": "SUT", "question_type": "私有协议类", "target_document": "sut_spec.md", "difficulty": "简单", "expected_keypoints": "校园内遥控共享单车控制协议", "should_refuse": False, "section": "sut_demo_questions"},
    {"id": 62, "question": "SUT 为什么要支持 Quiet-Unlock？", "protocol_group": "SUT", "question_type": "机制类", "target_document": "sut_spec.md", "difficulty": "简单", "expected_keypoints": "宿舍区夜间静音开锁、减少噪音", "should_refuse": False, "section": "sut_demo_questions"},
    {"id": 63, "question": "SUT 中 rush 和 festival 两种抖动模式有什么区别？", "protocol_group": "SUT", "question_type": "对比类", "target_document": "sut_spec.md", "difficulty": "中等", "expected_keypoints": "抖动范围不同、适用校园场景不同", "should_refuse": False, "section": "sut_demo_questions"},
    {"id": 64, "question": "SUT 中什么情况下可能返回 475 Quiet_Hours_Restricted？", "protocol_group": "SUT", "question_type": "规则类", "target_document": "sut_spec.md", "difficulty": "中等", "expected_keypoints": "宿舍区夜间静默时段不允许高提示音鸣笛或强提示开锁", "should_refuse": False, "section": "sut_demo_questions"},
    {"id": 65, "question": "SUT 中 Trace-Echo 会返回什么类型的诊断信息？", "protocol_group": "SUT", "question_type": "字段类", "target_document": "sut_spec.md", "difficulty": "中等", "expected_keypoints": "认证、定位、策略、抖动、执行等诊断信息", "should_refuse": False, "section": "sut_demo_questions"},
    {"id": 66, "question": "SUT 是否适合直接说明真实共享单车系统的所有实现细节？", "protocol_group": "SUT", "question_type": "证据不足类", "target_document": "sut_spec.md", "difficulty": "中等", "expected_keypoints": "这是演示协议，不应外推为真实系统完整实现", "should_refuse": True, "section": "sut_demo_questions"}
]


def build_markdown(rows: list[dict]) -> str:
    sections = {
        'rfc_questions': '## 2. RFC 标准文档问题（50 题）',
        'refusal_questions': '## 3. 证据不足 / 保守回答测试题（10 题）',
        'sut_demo_questions': '## 4. 私有协议 SUT 演示问题集（6 题）',
    }
    lines = [
        '# 测试问题集（第二版）',
        '',
        '本文档整理当前 RAG 项目的第二版测试问题集，用于：',
        '',
        '- 功能验证',
        '- 检索效果评估',
        '- 回答质量人工评分',
        '- 论文中的数据统计与图表生成',
        '',
        '问题集同时覆盖：',
        '- RFC 标准文档语料',
        '- 保守回答测试题',
        '- 私有演示协议 `SUT`',
        '',
        '---',
        '',
        '## 1. 使用说明',
        '',
        '### 1.1 目标',
        '',
        '本测试问题集用于评估系统在以下方面的表现：',
        '',
        '- 是否命中正确协议文档',
        '- 是否能根据上下文给出结构化回答',
        '- 是否能完成跨 RFC / 跨协议对比',
        '- 是否能在证据不足时保守回答',
        '- 是否能覆盖自定义私有协议文档的问答场景',
        '',
        '### 1.2 推荐评测维度',
        '',
        '- 是否回答正确',
        '- 是否命中目标 RFC / 文档',
        '- 回答是否完整',
        '- 是否存在明显幻觉',
        '- 首字响应时间',
        '- 总耗时',
        '- 检索来源数',
        '',
        '---',
        ''
    ]
    grouped = {'rfc_questions': [], 'refusal_questions': [], 'sut_demo_questions': []}
    for row in rows:
        grouped[row['section']].append(row)
    for key in ['rfc_questions', 'refusal_questions', 'sut_demo_questions']:
        lines.append(sections[key])
        lines.append('')
        lines.append('| ID | 问题 | 协议类别 | 题型 | 目标文档 | 难度 | 预期要点 | 是否应保守回答 |')
        lines.append('|---|---|---|---|---|---|---|---|')
        for row in grouped[key]:
            lines.append(f"| {row['id']} | {row['question']} | {row['protocol_group']} | {row['question_type']} | {row['target_document']} | {row['difficulty']} | {row['expected_keypoints']} | {'是' if row['should_refuse'] else '否'} |")
        lines.extend(['', '---', ''])
    lines.extend([
        '## 5. 第二版测试集的特点',
        '',
        '1. 补足了 DNS、TLS、TCP、UDP、IP、ICMP、ARP 等弱协议组；',
        '2. 补足了字段类、规则类、综合类和证据不足类问题；',
        '3. 增强了跨协议综合题与保守回答测试；',
        '4. 保持私有协议 SUT 题量精简，仅用于演示补充。',
        '',
        '---',
        '',
        '## 6. 使用建议',
        '',
        '- 正式实验主体：RFC 标准题 + 保守回答题',
        '- 演示补充：SUT 私有协议题',
        '- 自动评测：使用 `scripts/run_eval.py`',
        '- 人工评分：使用 `manual_scoring_template.csv` 或扩展版模板',
        '- 图表生成：使用 `scripts/plot_eval_figures.py`',
    ])
    return '\n'.join(lines) + '\n'


def main() -> None:
    rows = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    keep_ids = {row['id'] for row in rows}
    rows = [row for row in rows if row['id'] <= 30 or row['section'] == 'sut_demo_questions']
    existing_ids = {row['id'] for row in rows}
    for row in NEW_QUESTIONS:
        if row['id'] not in existing_ids:
            rows.append(row)
    rows.sort(key=lambda x: x['id'])

    JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')

    fieldnames = ['id','question','protocol_group','question_type','target_document','difficulty','expected_keypoints','should_refuse','section']
    with CSV_PATH.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    MD_PATH.write_text(build_markdown(rows), encoding='utf-8')
    print(f'[OK] Updated question set to {len(rows)} items.')


if __name__ == '__main__':
    main()
