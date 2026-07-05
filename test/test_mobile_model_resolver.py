import json

from app.services.mobile_model_resolver import (
    MobileModelResolver,
    extract_model_codes,
    normalize_model_code,
    resolve_mobile_model_from_user_agent,
)


def write_cache(tmp_path, mapping):
    cache_path = tmp_path / "mobile_models.json"
    cache_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    return cache_path


def test_normalize_model_code_removes_spaces_and_uppercases():
    assert normalize_model_code(" ana al00 ") == "ANAAL00"


def test_extract_model_codes_keeps_android_model_tokens():
    ua = (
        "Mozilla/5.0 (Linux; Android 14; Xiaomi 14 Build/UKQ1.230917.001; wv) "
        "AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
    )

    codes = extract_model_codes(ua)

    assert "Xiaomi14" in codes
    assert "UKQ1.230917.001" in codes
    assert "Android" not in codes
    assert "Mobile" not in codes


def test_resolves_huawei_model_from_exact_cached_code(tmp_path):
    cache_path = write_cache(tmp_path, {
        "ANA-AL00": {
            "brand_title": "Huawei",
            "model_name": "P40",
            "ver_name": "ANA-AL00",
        }
    })
    ua = "Mozilla/5.0 (Linux; Android 10; ANA-AL00 Build/HUAWEIANA-AL00) Mobile"

    resolved = resolve_mobile_model_from_user_agent(ua, cache_path=cache_path)

    assert resolved == {
        "device_model_code": "ANA-AL00",
        "device_model_name": "P40",
        "device_brand_name": "Huawei",
        "device_display_name": "Huawei P40 / ANA-AL00",
    }


def test_resolves_samsung_model_from_exact_cached_code(tmp_path):
    cache_path = write_cache(tmp_path, {
        "SM-G9980": {
            "brand_title": "Samsung",
            "model_name": "Galaxy S21 Ultra",
            "ver_name": "SM-G9980",
        }
    })
    ua = "Mozilla/5.0 (Linux; Android 13; SM-G9980 Build/TP1A.220624.014) Mobile"

    resolved = MobileModelResolver(cache_path).resolve(ua)

    assert resolved["device_display_name"] == "Samsung Galaxy S21 Ultra / SM-G9980"
    assert resolved["device_model_code"] == "SM-G9980"


def test_unknown_user_agent_returns_empty_dict(tmp_path):
    cache_path = write_cache(tmp_path, {
        "ANA-AL00": {"brand_title": "Huawei", "model_name": "P40", "ver_name": "ANA-AL00"}
    })

    assert resolve_mobile_model_from_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", cache_path) == {}


def test_resolver_does_not_guess_partial_codes(tmp_path):
    cache_path = write_cache(tmp_path, {
        "ANA-AL00": {"brand_title": "Huawei", "model_name": "P40", "ver_name": "ANA-AL00"}
    })
    ua = "Mozilla/5.0 (Linux; Android 10; ANA Build/X) Mobile"

    assert resolve_mobile_model_from_user_agent(ua, cache_path) == {}


def test_resolver_uses_csv_model_as_code_not_version_name(tmp_path):
    cache_path = write_cache(tmp_path, {
        "ANA-AL00": {
            "model": "ANA-AL00",
            "brand_title": "Huawei",
            "model_name": "P40",
            "ver_name": "全网通版",
        }
    })
    ua = "Mozilla/5.0 (Linux; Android 10; ANA-AL00 Build/HUAWEIANA-AL00) Mobile"

    resolved = resolve_mobile_model_from_user_agent(ua, cache_path=cache_path)

    assert resolved["device_model_code"] == "ANA-AL00"
    assert resolved["device_model_name"] == "P40"
    assert resolved["device_display_name"] == "Huawei P40 / ANA-AL00"

