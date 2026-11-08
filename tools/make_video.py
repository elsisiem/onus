"""Build the 1-minute submission video from the live UI: CDP screenshots + Gemini TTS voice-over + ffmpeg.

usage: ../.venv/bin/python tools/make_video.py   (server running on :8787, hackathon Chromium on :9222)
"""
import base64, json, os, subprocess, sys, time, urllib.request, wave
import websocket, imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "runs", "video"); os.makedirs(OUT, exist_ok=True)
env = dict(l.strip().split("=", 1) for l in open(os.path.join(os.path.dirname(ROOT), ".env")) if "=" in l)
FF = imageio_ffmpeg.get_ffmpeg_exe()

# (seconds, js to run before the shot, narration line)
SHOTS = [
    (8, "window.scrollTo(0,0)", "Robodebt averaged people's income, and sent four hundred and seventy thousand unlawful debts. AI will write code like that next. CI was green. The law wasn't."),
    (9, "document.querySelector('[data-section=act]')?.scrollIntoView({block:'start'})", "ONUS reads the law first. Meta's Muse read all 828 pages of the Act in one call, every quote verified."),
    (9, "document.querySelector('[data-section=letter]')?.scrollIntoView({block:'start'})", "This pull request would mail Sara a debt of $4,875. The law says zero. Her twin has identical inputs and a different lawful debt."),
    (9, "document.querySelector('[data-section=snap]')?.scrollIntoView({block:'start'})", "SubQ Snap names the clause, catches the undisclosed change, and blocks it, in under half a second."),
    (9, "document.querySelector('[data-section=cert]')?.scrollIntoView({block:'start'})", "Gemini's red team: repo tests caught zero of three. ONUS caught three of three, and signs it."),
    (6, "window.scrollTo(0,0)", "ONUS. The burden of proof is on the code."),
]


def cdp_tab():
    tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list"))
    t = next((t for t in tabs if "127.0.0.1:8787" in t["url"]), None)
    if not t:
        req = urllib.request.Request("http://127.0.0.1:9222/json/new?http://127.0.0.1:8787/", method="PUT")
        t = json.load(urllib.request.urlopen(req)); time.sleep(4)
    return websocket.create_connection(t["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)


_id = [0]
def call(ws, method, **params):
    _id[0] += 1; ws.send(json.dumps({"id": _id[0], "method": method, "params": params}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == _id[0]:
            return m.get("result", {})


def tts(text, path):
    body = {"contents": [{"parts": [{"text": "Read in a calm, precise narrator voice: " + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}}}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": env["GEMINI_API_KEY"]})
    for attempt in range(5):
        try:
            part = json.load(urllib.request.urlopen(req, timeout=90))["candidates"][0]["content"]["parts"][0]["inlineData"]
            break
        except Exception as e:
            print("tts retry", attempt + 1, repr(e)[:80]); time.sleep(2 + attempt * 2)
    else:
        raise RuntimeError("TTS failed after retries")
    raw = base64.b64decode(part["data"])
    if raw[:4] == b"RIFF":
        open(path, "wb").write(raw)
    else:
        with wave.open(path, "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw)


def main():
    ws = cdp_tab()
    call(ws, "Emulation.setDeviceMetricsOverride", width=1600, height=900, deviceScaleFactor=1, mobile=False)
    call(ws, "Page.navigate", url="http://127.0.0.1:8787/"); time.sleep(6)
    segs = []
    for i, (sec, js, line) in enumerate(SHOTS):
        call(ws, "Runtime.evaluate", expression=js); time.sleep(1.5)
        png = os.path.join(OUT, f"s{i}.png")
        open(png, "wb").write(base64.b64decode(call(ws, "Page.captureScreenshot", format="png")["data"]))
        wav = os.path.join(OUT, f"s{i}.wav"); tts(line, wav)
        seg = os.path.join(OUT, f"s{i}.mp4")
        subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", png, "-i", wav,
                        "-filter_complex", "[1:a]atempo=1.12,apad=pad_dur=0.4[a]", "-map", "0:v", "-map", "[a]", "-shortest",
                        "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", seg], check=True)
        segs.append(seg); print("segment", i, "ok")
    lst = os.path.join(OUT, "list.txt"); open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    final = os.path.join(ROOT, "runs", "onus_demo.mp4")
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", final], check=True)
    print("video:", final)


if __name__ == "__main__":
    main()
