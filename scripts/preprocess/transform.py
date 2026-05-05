def parse_mongo_date(value):
    if isinstance(value, dict):
        return value.get("$date", "")
    return str(value) if value else ""


def iso_to_date(iso_str):
    return iso_str[:10] if iso_str else None


def classify_audio(result_record):
    """
    conversation:        lmsType == "conversation"  (structured dialogue, grammar+pron scoring)
    pronunciation_drill: additionalData.speaking    (phonetic accuracy drills)
    brainstorm:          additionalData.brainstorm (nhìn ảnh / gợi ý, nói các từ mục tiêu)
    free_speaking:       additionalData.warmup only (nói mở / icebreaker, không phải brainstorm)
    other:               no recognised lmsType or additionalData
    """
    if result_record.get("lmsType") == "conversation":
        return "conversation"
    ad = (result_record.get("result") or {}).get("additionalData") or {}
    if "speaking" in ad:
        return "pronunciation_drill"
    if "brainstorm" in ad:
        return "brainstorm"
    if "warmup" in ad:
        return "free_speaking"
    return "other"


def extract_user_answer_type(additional_data):
    if not isinstance(additional_data, dict):
        return None
    for v in additional_data.values():
        if isinstance(v, dict):
            uat = (v.get("result") or {}).get("userAnswerType")
            if uat:
                return uat
    return None
