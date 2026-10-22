import json


def _mood(e):
    return {k: e[k] for k in ["valence", "arousal", "calmness", "focus", "stress", "confidence"]}


def test_health_and_meta(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["emotion_model"]["is_demo_baseline"] and h["llm"] == "local-rules"
    assert client.get("/api/meta").json()["counts"]["endpoints"] >= 20


def test_auth_register_login_and_errors(client):
    body = {"email": "Ada@Example.com", "password": "correct-horse", "display_name": "Ada"}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201 and r.json()["user"]["email"] == "ada@example.com"
    assert client.post("/api/auth/register", json=body).status_code == 409
    ok = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "correct-horse"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong-password"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}).status_code == 401
    short = client.post("/api/auth/register", json={**body, "email": "b@example.com", "password": "short"})
    assert short.status_code == 422 and short.json()["detail"] == "Invalid request"


def test_protected_routes_need_valid_token(client):
    assert client.get("/api/user/profile").status_code == 401
    assert client.get("/api/user/profile", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_password_is_hashed(client, auth):
    from app.db.models import User
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        u = db.query(User).filter(User.email == "ada@example.com").first()
        assert u and u.password_hash.startswith("$2") and "correct-horse" not in u.password_hash


def test_demo_window_flows_through_pipeline(client):
    r = client.get("/api/eeg/demo/window", params={"scenario": "stressed", "t": 4})
    assert r.status_code == 200
    d = r.json()
    assert d["emotion"]["arousal"] > 0.6 and d["scenario"] == "stressed" and len(d["waveform"]["channels"]) == 4
    assert set(d["features"]["relative_band_power"]) == {"delta", "theta", "alpha", "beta", "gamma"}
    calm = client.get("/api/eeg/demo/window", params={"scenario": "calm", "t": 4}).json()
    assert calm["emotion"]["arousal"] < d["emotion"]["arousal"]
    assert client.get("/api/eeg/demo/window", params={"scenario": "bogus"}).status_code == 422
    assert client.get("/api/eeg/demo/window", params={"window_s": 99}).status_code == 422


def test_analyze_raw_samples_and_validation(client, make_window):
    raw = make_window("focused")
    ok = client.post("/api/eeg/analyze", json={"fs": 256, "samples": {c: raw[i].tolist() for i, c in enumerate(["TP9", "AF7", "AF8", "TP10"])}})
    assert ok.status_code == 200 and ok.json()["emotion"]["label"]
    assert client.post("/api/eeg/analyze", json={"fs": 256, "samples": {"a": [1.0] * 10}}).status_code == 422
    assert client.post("/api/eeg/analyze", json={"fs": 256, "samples": {"a": [1.0] * 600, "b": [1.0] * 500}}).status_code == 422


def test_emotion_predict_endpoint(client):
    vec = client.get("/api/eeg/demo/window", params={"scenario": "calm"}).json()["features"]["vector"]
    r = client.post("/api/emotion/predict", json={"features": vec})
    assert r.status_code == 200 and 0 <= r.json()["valence"] <= 1
    assert client.post("/api/emotion/predict", json={"features": {"rel_alpha": 1}}).status_code == 422


def test_recommend_public_and_validation(client):
    e = client.get("/api/eeg/demo/window", params={"scenario": "stressed", "t": 2}).json()["emotion"]
    r = client.post("/api/music/recommend", json={"emotion": _mood(e), "mode": "shift", "target": "calm", "shift": 1.0})
    assert r.status_code == 200
    d = r.json()
    assert d["plan"]["target_key"] == "calm" and len(d["playlist"]) == 4 and d["profile"]["bpm"] < 100
    assert [s["stage"] for s in d["explanation"]["steps"]][0] == "EEG signal" or d["explanation"]["steps"]
    assert client.post("/api/music/recommend", json={"mode": "match"}).status_code == 422
    assert client.post("/api/music/recommend", json={"emotion": {**_mood(e), "valence": 3}}).status_code == 422


def test_text_fusion_changes_recommendation(client):
    e = client.get("/api/eeg/demo/window", params={"scenario": "calm", "t": 2}).json()["emotion"]
    base = client.post("/api/music/recommend", json={"emotion": _mood(e)}).json()
    fused = client.post("/api/music/recommend", json={"emotion": _mood(e), "text": "I'm anxious and overwhelmed, want to focus, piano"}).json()
    assert fused["fusion_weights"].get("language", 0) > 0 and fused["nlp"]["intent"] == "focus"
    assert fused["fused_state"]["stress"] > base["fused_state"]["stress"]
    only_text = client.post("/api/music/recommend", json={"text": "I feel exhausted"})
    assert only_text.status_code == 200 and only_text.json()["fusion_weights"] == {"language": 1.0}


def test_generate_audio_save_feedback_history(client, auth):
    e = client.get("/api/eeg/demo/window", params={"scenario": "excited", "t": 1}).json()["emotion"]
    body = {"emotion": _mood(e), "mode": "match", "duration_s": 8}
    g = client.post("/api/music/generate", json=body, headers=auth)
    assert g.status_code == 200, g.text
    tr = g.json()["track"]
    audio = client.get(tr["audio_url"])
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/wav" and audio.content[:4] == b"RIFF"
    assert tr["id"] and client.post("/api/music/save", json={"track_id": tr["id"]}, headers=auth).json()["saved"] is True
    assert client.post("/api/music/feedback", json={"track_id": tr["id"], "rating": 4, "mood_after": {"valence": .6, "arousal": .5}}, headers=auth).status_code == 201
    hist = client.get("/api/music/history", headers=auth).json()
    assert len(hist) == 1 and hist[0]["saved"] is True
    # same request is served from cache (identical audio id); new variation gives a different take
    assert client.post("/api/music/generate", json=body, headers=auth).json()["track"]["audio_id"] == tr["audio_id"]
    assert client.post("/api/music/generate", json={**body, "variation": 1}, headers=auth).json()["track"]["audio_id"] != tr["audio_id"]
    assert client.post("/api/music/generate", json={**body, "preset_id": "nope"}, headers=auth).status_code == 422
    assert client.post("/api/music/generate", json={**body, "provider": "huggingface-musicgen"}, headers=auth).json()["provider_note"]
    assert client.get("/api/music/audio/doesnotexist.wav").status_code == 404
    assert client.get("/api/music/audio/..%2F..%2Fsecret.wav").status_code in (404, 422)


def test_users_cannot_touch_each_others_tracks(client, auth):
    e = client.get("/api/eeg/demo/window").json()["emotion"]
    tid = client.post("/api/music/generate", json={"emotion": _mood(e), "duration_s": 8}, headers=auth).json()["track"]["id"]
    other = {"Authorization": "Bearer " + client.post("/api/auth/demo").json()["access_token"]}
    assert client.post("/api/music/save", json={"track_id": tid}, headers=other).status_code == 404
    assert client.post("/api/music/feedback", json={"track_id": tid, "rating": 5}, headers=other).status_code == 404


def test_sessions_demo_and_upload(client, auth):
    s = client.post("/api/eeg/session", json={"duration_s": 20, "scenario": "focused"}, headers=auth)
    assert s.status_code == 201 and s.json()["n_windows"] == 9
    sid = s.json()["id"]
    got = client.get(f"/api/eeg/session/{sid}", headers=auth).json()
    assert len(got["windows"]) == 9 and got["summary"]["dominant_state"]
    assert any(x["id"] == sid for x in client.get("/api/eeg/sessions", headers=auth).json())
    other = {"Authorization": "Bearer " + client.post("/api/auth/demo").json()["access_token"]}
    assert client.get(f"/api/eeg/session/{sid}", headers=other).status_code == 404

    rows = ["time,TP9,AF7,AF8,TP10"] + [f"{i / 256:.5f},{i % 40 - 20},{i % 33 - 16},{i % 27 - 13},{i % 51 - 25}" for i in range(256 * 5)]
    up = client.post("/api/eeg/upload", files={"file": ("rec.csv", "\n".join(rows))}, headers=auth)
    assert up.status_code == 201 and up.json()["source"] == "csv"
    js = json.dumps({"fs": 128, "data": {"AF3": [float(i % 17) for i in range(128 * 5)], "AF4": [float(i % 13) for i in range(128 * 5)]}})
    assert client.post("/api/eeg/upload", files={"file": ("rec.json", js)}, headers=auth).status_code == 201


def test_upload_rejections(client, auth):
    assert client.post("/api/eeg/upload", files={"file": ("rec.exe", b"x")}, headers=auth).status_code == 415
    assert client.post("/api/eeg/upload", files={"file": ("rec.csv", "a,b\n1,2\n")}, headers=auth).status_code == 422
    big = b"time,a\n" + b"0,1\n" * (6 * 1024 * 1024 // 4)
    assert client.post("/api/eeg/upload", files={"file": ("big.csv", big)}, headers=auth).status_code == 413
    assert client.post("/api/eeg/upload", files={"file": ("rec.csv", "x")}).status_code == 401


def test_profile_preferences_and_analytics(client, auth):
    p = client.put("/api/user/preferences", json={"genres": [" Piano ", "Ambient"], "default_mode": "shift"}, headers=auth)
    assert p.status_code == 200 and p.json()["genres"] == ["piano", "ambient"]
    assert client.get("/api/user/profile", headers=auth).json()["preferences"]["default_mode"] == "shift"
    client.post("/api/eeg/session", json={"duration_s": 12}, headers=auth)
    a = client.get("/api/user/analytics", headers=auth).json()
    assert a["totals"]["sessions"] == 1 and a["mood_trend"] and a["state_distribution"]
    assert client.get("/api/mood/history", headers=auth).json()


def test_guide_and_nlp_endpoints(client):
    c = client.post("/api/guide/chat", json={"message": "What does alpha activity represent?"})
    assert c.status_code == 200 and c.json()["sources"] and "Established science" in c.json()["answer"]
    assert client.post("/api/guide/chat", json={"message": ""}).status_code == 422
    assert client.get("/api/guide/suggestions").json()
    assert client.post("/api/nlp/parse", json={"text": "I feel sad, I want to feel energised"}).json()["intent"] == "energize"


def test_internal_errors_do_not_leak_details(client, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import engine

    def boom(*a, **k):
        raise RuntimeError("secret path /etc/passwd")
    monkeypatch.setattr(engine, "demo_window", boom)
    r = TestClient(app, raise_server_exceptions=False).get("/api/eeg/demo/window")
    assert r.status_code == 500 and "secret" not in r.text


def test_guide_tolerates_partial_context(client):
    r = client.post("/api/guide/chat", json={"message": "Why this music?", "context": {"profile": {"bpm": 90, "key": "F"}, "emotion": {"label": "Calm", "valence": .6, "arousal": .3, "focus": .5, "stress": .2, "confidence": .5}}})
    assert r.status_code == 200
