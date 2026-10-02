from app.adapters.llm import _fallback, SYSTEM
from app.services.chunking import chunk_blocks
from app.services.web_content import extract_html


def test_no_knowledge_fallback_supports_regular_chat_without_hash_star_noise():
    answer = _fallback("你好", [], [])
    assert "可以正常交流" in answer
    assert "#" not in answer
    assert "**" not in answer
    assert "请先上传相关资料" not in answer
    assert "必须只依据" not in SYSTEM


def test_web_search_ingestion_keeps_policy_phrase_across_chunk_boundaries():
    paragraph = (
        "开展规划实施情况动态监测、中期评估和总结评估，加强形势跟踪和风险研判，"
        "根据监测评估情况及时提出加强和改进规划实施的政策举措。经党中央同意后，"
        "中期评估情况依法向全国人民代表大会常务委员会报告，总结评估报告依法提交全国人民代表大会，"
        "自觉接受人大监督。经评估确需对本规划进行调整时，由国务院提出调整方案，"
        "报党中央同意后，提请全国人民代表大会常务委员会审查和批准。"
        "把完善党和国家监督体系融入规划实施之中，发挥纪检监察机关和审计机关等对规划实施的监督作用。"
    )
    html = f"<html><head><title>测试规划纲要</title></head><body><article><h2>第四节 加强规划实施监测评估和监督</h2><p>{paragraph}</p></article></body></html>"
    _, extracted = extract_html(html, "https://example.gov.cn/policy")
    assert paragraph in extracted.text
    result = chunk_blocks(extracted.blocks, max_chars=120, overlap_chars=0, source_method=extracted.source_method)
    child_texts = [c.text for c in result.chunks if c.chunk_type == "child"]
    assert any("报党中央同意后，提请全国人民代表大会常务委员会审查和批准" in t for t in child_texts)
    assert not any(t.endswith("由国务院提出调整方案，报") for t in child_texts)


def test_extract_html_falls_back_to_full_visible_text_when_page_has_no_p_tags():
    content = "第一段正文。" * 40 + "完整网页正文结尾。"
    html = f"<html><head><title>无段落网页</title></head><body><div id='content'>{content}</div></body></html>"
    _, extracted = extract_html(html, "https://example.gov.cn/no-p")
    assert "完整网页正文结尾" in extracted.text
    assert len(extracted.text) >= len(content)
