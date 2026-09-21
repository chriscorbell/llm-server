import json, os, subprocess, sys, copy, time, signal
S = os.path.dirname(os.path.abspath(__file__))
AGENT = f"{S}/agent"; PROJ = f"{S}/proj"; OUT = f"{S}/runs"; os.makedirs(OUT, exist_ok=True)
base = json.load(open(os.path.expanduser("~/.pi/agent/settings.json")))
PKGS = base["packages"]
def short(p):
    n = p.removeprefix("npm:"); n = n.rsplit("@", 1)[0]; return n
def run(label, packages, extra=()):
    s = copy.deepcopy(base); s["packages"] = packages
    json.dump(s, open(f"{AGENT}/settings.json", "w"), indent=2)
    env = dict(os.environ, PI_CODING_AGENT_DIR=AGENT)
    cmd = ["pi", "-p", "--mode", "json", "--thinking", "off", "--no-session", *extra, "Reply with only the word OK."]
    log = f"{OUT}/{label.replace(' ', '_').replace('/', '_')}.jsonl"
    t = time.time(); hung = False
    with open(log, "w") as fo, open(log + ".err", "w") as fe:
        p = subprocess.Popen(cmd, cwd=PROJ, env=env, stdout=fo, stderr=fe, start_new_session=True)
        try: p.wait(timeout=150)
        except subprocess.TimeoutExpired:
            hung = True; os.killpg(p.pid, signal.SIGKILL); p.wait()
    inp = cache = out = None
    for line in open(log):
        try: e = json.loads(line)
        except: continue
        if e.get("type") == "message_end" and e.get("message", {}).get("role") == "assistant":
            u = e["message"].get("usage") or {}
            inp, cache, out = u.get("input"), u.get("cacheRead"), u.get("output")
    prompt = (inp or 0) + (cache or 0)
    print(f"{label:34} prompt={prompt:6}  in={inp} cached={cache} out={out}  {time.time()-t:5.1f}s{'  HUNG(killed)' if hung else ''}", flush=True)
    return prompt
which = sys.argv[1] if len(sys.argv) > 1 else "all"
if which in ("baseline", "all"):
    run("all packages", PKGS)
    run("all packages -nc", PKGS, ("-nc",))
    run("no packages", [])
    run("no packages -ne", [], ("-ne",))
if which == "all":
    for p in PKGS:
        run(f"minus {short(p)}", [q for q in PKGS if q != p])
    for p in PKGS:
        run(f"only {short(p)}", [p])
print("DONE", flush=True)
