"""Deterministic guards for steps 1-4. Pure checks, no AI judgement.

Every function returns a list of Finding. level is "block" (stops the step) or "warn" (shown to the human).
Each finding says where, which rule, what is wrong and how to fix it, so a human can act on it.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Finding:
    level: str          # block | warn
    code: str
    where: str
    message: str
    fix: str = ""

    def as_dict(self):
        return asdict(self)


def block(code, where, message, fix=""):
    return Finding("block", code, where, message, fix)


def warn(code, where, message, fix=""):
    return Finding("warn", code, where, message, fix)


# ---------------------------------------------------------------- loading helpers

def load_yaml(config_dir: Path, name: str):
    return yaml.safe_load((Path(config_dir) / name).read_text(encoding="utf-8"))


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schema_findings(name: str, data, where: str):
    schema = load_json(ROOT / "schemas" / f"{name}.schema.json")
    out = []
    for err in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "(top level)"
        out.append(block("schema", f"{where}: {loc}", err.message, "Fix the field so it matches the schema."))
    return out


# ---------------------------------------------------------------- text helpers

STOP = set("""a an the and or but if then so of to in on at by for from with without into over under about as is are was were be been
being it its this that these those there here you your yours we our they their he she his her i me my not no yes do does did done
have has had will would can could should may might must just only also more most less than too very how what when where which who
whom why all any each every some many much one two""".split())

LABEL_WORDS = r"(?:step|tip|point|reason|myth|mistake|rule|part|slide|number|fact|way|lesson|day|week)"
NUM_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)")
_MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DATE_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+" + _MON + r",?\s+\d{4}\b|\b" + _MON + r"\s+\d{1,2},?\s+\d{4}\b|\b" + _MON + r"\s+\d{4}\b|\b(?:19|20)\d{2}\b",
    re.I,
)
SPELLED_QTY = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand",
               "lakh", "crore", "million", "billion", "trillion", "percent", "per cent"]


def stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def content_stems(text: str) -> set[str]:
    return {stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 2}


def norm_number(raw: str):
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def numbers_in(text: str, allow_labels: bool = True):
    """Numeric tokens in text. A bare label like 'Step 2' is not a claim, so it is skipped."""
    found = []
    for m in NUM_RE.finditer(text):
        before = text[max(0, m.start() - 12): m.start()].lower()
        if allow_labels and re.search(LABEL_WORDS + r"\s*#?$", before):
            continue
        v = norm_number(m.group(1))
        if v is not None:
            found.append((m.group(1), v))
    return found


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


# ---------------------------------------------------------------- Step 1

def check_topic(run_dir: Path, **_):
    p = run_dir / "01_research" / "topic.json"
    if not p.exists():
        return [block("missing_file", str(p.name), "topic.json has not been written.",
                      "A human must state or pick the topic (discovery mode: pick from the candidates).")]
    return schema_findings("topic", load_json(p), "topic.json")


def _domain_tier(url: str, sources_cfg: dict):
    host = (urlparse(url).hostname or "").lower()

    def match(domains):
        return any(host == d or host.endswith("." + d) for d in domains)

    if match(sources_cfg.get("tier1", [])):
        return "tier1"
    if match(sources_cfg.get("tier2", []) or []):
        return "tier2"
    if match(sources_cfg.get("tier3_lead_only", [])):
        return "tier3"
    return None


def check_ledger(run_dir: Path, config_dir: Path, final: bool = False, today: dt.date | None = None, **_):
    """final=True is the Gate 1 standard: every fact decided, conflicts resolved, minimums met."""
    today = today or dt.date.today()
    p = run_dir / "01_research" / "fact_ledger.json"
    if not p.exists():
        return [block("missing_file", "fact_ledger.json", "The fact ledger has not been written.",
                      "Run the research skill to produce it.")]
    data = load_json(p)
    out = schema_findings("fact_ledger", data, "fact_ledger.json")
    if out:
        return out
    cfg = load_yaml(config_dir, "research-sources.yaml")
    rules = cfg["rules"]
    facts = data["facts"]
    ids = [f["id"] for f in facts]
    if len(ids) != len(set(ids)):
        out.append(block("duplicate_id", "fact_ledger.json", "Fact ids must be unique."))

    approved = []
    for f in facts:
        w = f"fact {f['id']}"
        src = f["source"]
        url = src.get("url", "")
        tier_by_domain = _domain_tier(url, cfg) if url else None

        # a fact may only be APPROVED from a source the content team allowed
        if f["status"] == "approved":
            approved.append(f)
            if src["tier"] == "internal":
                if not src.get("provided_by") or not src.get("file"):
                    out.append(block("internal_unattributed", w, "Internal source must name who supplied it and the file.",
                                     "Add source.provided_by and source.file."))
            else:
                if not url.startswith("https://"):
                    out.append(block("source_url", w, "Approved fact needs an https source URL.", "Add the exact page URL."))
                elif tier_by_domain is None:
                    out.append(block("source_not_allowed", w, f"Domain {urlparse(url).hostname} is not in research-sources.yaml.",
                                     "Use an approved source, or ask the content team to add the domain."))
                elif tier_by_domain == "tier3":
                    out.append(block("lead_only_source", w, "Media sources are leads only; they cannot back an approved fact.",
                                     "Find the primary source (regulator, exchange, AMC) and cite that."))
                elif tier_by_domain != src["tier"]:
                    out.append(block("tier_mismatch", w, f"Declared {src['tier']} but domain is {tier_by_domain}.", "Correct the tier."))
            ex = f.get("evidence_excerpt", "")
            if not ex.strip():
                out.append(block("no_evidence", w, "Approved fact has no evidence excerpt.",
                                 "Add the short passage (up to %d words) that supports it." % rules["max_excerpt_words"]))
            elif len(ex.split()) > rules["max_excerpt_words"]:
                out.append(block("excerpt_too_long", w, f"Excerpt is {len(ex.split())} words; limit {rules['max_excerpt_words']}.",
                                 "Shorten it and keep the paraphrase in `statement`."))
            nums = f.get("numbers", [])
            for n in nums:
                if "as_of" not in n:
                    out.append(block("number_no_date", w, f"Number {n['raw']} has no as_of date.", "Every figure needs the date it is true for."))
                else:
                    age = (today - dt.date.fromisoformat(n["as_of"])).days
                    if age > rules["max_age_days_for_figures"] and not f.get("review_note"):
                        out.append(block("stale_figure", w, f"Figure {n['raw']} is {age} days old.",
                                         "Refresh it, or a human adds a review_note accepting it."))
            # every figure in the statement must be declared in numbers[] so the script validator can trace it
            declared = {norm_number(n["raw"].replace("%", "").replace("₹", "").strip()) for n in nums}
            for raw, val in numbers_in(DATE_RE.sub(" ", f["statement"]), allow_labels=False):
                if val not in declared:
                    out.append(block("undeclared_number", w, f"Statement contains {raw} that is not listed in numbers[].",
                                     "List every figure with its as_of date."))
            if not f.get("reviewed_by"):
                out.append(block("no_reviewer", w, "Approved fact has no reviewed_by.", "A human must review each fact."))
    if final:
        for f in facts:
            if f["status"] == "proposed":
                out.append(block("undecided", f"fact {f['id']}", "Fact is still 'proposed'.", "A human approves or rejects every fact before Gate 1."))
        for c in data.get("conflicts", []):
            if not c.get("resolution") or not c.get("resolved_by"):
                out.append(block("conflict_open", "conflicts", f"Sources disagree ({', '.join(c['fact_ids'])}): {c['description']}",
                                 "A human records a resolution and who resolved it."))
        if len(approved) < rules["min_approved_facts"]:
            out.append(block("too_thin", "fact_ledger.json", f"{len(approved)} approved facts; need {rules['min_approved_facts']}.",
                             "Research more, or narrow the topic."))
        firm = [f for f in approved if f["source"]["tier"] in ("tier1", "internal")]
        if len(firm) < rules["min_tier1_facts"]:
            out.append(block("weak_sourcing", "fact_ledger.json", f"{len(firm)} approved facts from primary or internal sources; need {rules['min_tier1_facts']}.",
                             "Add facts from regulators, exchanges or the team's own data."))
    return out


# ---------------------------------------------------------------- Step 2

def _approved_fact_ids(run_dir: Path):
    p = run_dir / "01_research" / "fact_ledger.json"
    return {f["id"] for f in load_json(p)["facts"] if f["status"] == "approved"} if p.exists() else set()


def check_angles(run_dir: Path, config_dir: Path, need_selection: bool = False, **_):
    p = run_dir / "02_ideation" / "angles.json"
    if not p.exists():
        return [block("missing_file", "angles.json", "angles.json has not been written.", "Run the ideation skill.")]
    data = load_json(p)
    out = schema_findings("angles", data, "angles.json")
    if out:
        return out
    types = load_yaml(config_dir, "content-types.yaml")["types"]
    approved = _approved_fact_ids(run_dir)
    for a in data["angles"]:
        w = f"angle {a['id']}"
        if a["format"] not in types:
            out.append(block("bad_format", w, f"'{a['format']}' is not a platform content type.", "Use one of: " + ", ".join(types)))
        if len(a["core_message"].split()) > 30:
            out.append(block("message_long", w, "Core message is over 30 words.", "One sentence, one idea."))
        kids = {k["id"] for k in a["key_points"]}
        if len(kids) != len(a["key_points"]):
            out.append(block("dup_key_point", w, "Duplicate key point ids."))
        for k in a["key_points"]:
            for fid in k["fact_ids"]:
                if fid not in approved:
                    out.append(block("unapproved_fact", f"{w} {k['id']}", f"Cites {fid}, which is not an approved fact.",
                                     "Cite only facts the human approved at Gate 1."))
    if len({a["id"] for a in data["angles"]}) != len(data["angles"]):
        out.append(block("dup_angle", "angles.json", "Duplicate angle ids."))
    if need_selection:
        sel = data.get("selected")
        if not sel:
            out.append(block("no_selection", "angles.json", "No angle has been selected by a human.", "A human picks one angle (and may edit it)."))
        elif sel["angle_id"] not in {a["id"] for a in data["angles"]}:
            out.append(block("bad_selection", "angles.json", f"Selected angle {sel['angle_id']} does not exist."))
    return out


# ---------------------------------------------------------------- Step 3

def check_lock(run_dir: Path, config_dir: Path, **_):
    p = run_dir / "03_approval" / "locked_brief.json"
    if not p.exists():
        return [block("missing_file", "locked_brief.json", "The brief has not been compiled.", "Run: engine.py lock <run>")]
    lb = load_json(p)
    out = schema_findings("locked_brief", lb, "locked_brief.json")
    if out:
        return out
    ids = {f["id"] for f in lb["facts"]}
    for k in lb["key_points"]:
        for fid in k["fact_ids"]:
            if fid not in ids:
                out.append(block("lock_fact_missing", k["id"], f"{fid} is not included in the lock."))
    for f in lb["facts"]:
        if f["status"] != "approved":
            out.append(block("lock_fact_status", f["id"], "Locked facts must be approved."))
    # the lock must match the live research and selection it claims to come from
    cf = lb["compiled_from"]
    for rel, key in (("01_research/fact_ledger.json", "fact_ledger_sha256"), ("02_ideation/angles.json", "angles_sha256")):
        if sha256_file(run_dir / rel) != cf.get(key):
            out.append(block("lock_stale", "locked_brief.json", f"{rel} changed after the brief was compiled.", "Re-run: engine.py lock <run>"))
    return out


# ---------------------------------------------------------------- Step 4

def _load_lock(run_dir: Path):
    return load_json(run_dir / "03_approval" / "locked_brief.json")


def check_storyline(run_dir: Path, **_):
    p = run_dir / "04_script" / "storyline.json"
    if not p.exists():
        return [block("missing_file", "storyline.json", "The storyline has not been written.", "Run the storyline skill.")]
    s = load_json(p)
    out = schema_findings("storyline", s, "storyline.json")
    if out:
        return out
    lb = _load_lock(run_dir)
    lb_hash = sha256_file(run_dir / "03_approval" / "locked_brief.json")
    if s["locked_brief_sha256"] != lb_hash:
        out.append(block("wrong_lock", "storyline.json", "Storyline was written against a different locked brief.", "Rewrite it against the current lock."))
    if squash(s["core_message"]) != squash(lb["core_message"]):
        out.append(block("message_changed", "storyline.json", "core_message does not match the locked message word for word.",
                         "Copy the locked core_message exactly."))
    kids = {k["id"] for k in lb["key_points"]}
    used = {a["key_point"] for a in s["arc"] if a["key_point"]}
    if used - kids:
        out.append(block("unknown_key_point", "storyline.json", f"Unknown key points: {sorted(used - kids)}"))
    if kids - used:
        out.append(block("key_point_missing", "storyline.json", f"Storyline never covers {sorted(kids - used)}.", "Every locked key point needs an act."))
    acts = [a["act"] for a in s["arc"]]
    if acts[0] != "hook":
        out.append(block("arc_start", "storyline.json", "Storyline must open with a hook."))
    if "cta" in acts and acts[-1] != "cta":
        out.append(block("arc_end", "storyline.json", "A cta, if present, must be the last act."))
    for a in s["arc"]:
        if a["act"] in ("point", "proof") and not a["key_point"]:
            out.append(block("act_unanchored", "storyline.json", f"A '{a['act']}' act has no key_point.", "Every point or proof act belongs to a locked key point."))
    return out


def check_script(run_dir: Path, config_dir: Path, **_):
    p = run_dir / "04_script" / "script.json"
    if not p.exists():
        return [block("missing_file", "script.json", "The script has not been written.", "Run the script skill.")]
    sc = load_json(p)
    out = schema_findings("script", sc, "script.json")
    if out:
        return out
    lb = _load_lock(run_dir)
    comp = load_yaml(config_dir, "compliance-rules.yaml")
    types = load_yaml(config_dir, "content-types.yaml")["types"]
    facts = {f["id"]: f for f in lb["facts"]}
    kps = {k["id"]: k for k in lb["key_points"]}
    beats = sc["beats"]

    # --- the script is written against THIS lock and says the locked message verbatim
    if sc["locked_brief_sha256"] != sha256_file(run_dir / "03_approval" / "locked_brief.json"):
        out.append(block("wrong_lock", "script.json", "Script was written against a different locked brief.", "Rewrite against the current lock."))
    if squash(sc["core_message"]) != squash(lb["core_message"]):
        out.append(block("message_changed", "script.json", "core_message differs from the locked message.", "Copy it exactly; do not reword."))
    if sc["format"] != lb["format"]:
        out.append(block("format_changed", "script.json", f"Format is {sc['format']} but the brief locked {lb['format']}."))

    # --- ids and ordering
    bids = [b["id"] for b in beats]
    if len(bids) != len(set(bids)):
        out.append(block("dup_beat", "script.json", "Duplicate beat ids."))
    disc = comp.get("sebi_disclosure", {})
    if disc.get("required"):
        if beats[0]["kind"] != "disclosure":
            out.append(block("disclosure_missing", "script.json",
                             "The first slide must be the SEBI disclosure slot (kind 'disclosure').",
                             "Add it first, with the slot text from compliance-rules.yaml, unchanged."))
        elif squash(beats[0]["text"]) != squash(disc.get("slot_text", "")):
            out.append(block("disclosure_altered", beats[0]["id"],
                             "The disclosure slide must be the placeholder text exactly. Real names and numbers are added at co-branding.",
                             "Use the slot_text from compliance-rules.yaml. Never write a registration number."))
    content = [b for b in beats if b["kind"] not in ("disclosure",)]
    if not content or content[0]["kind"] != "hook":
        out.append(block("no_hook", "script.json", "The first content beat (after the disclosure slot) must be the hook."))

    # --- length budget from the content type
    t = types.get(lb["format"])
    if t:
        n = sum(1 for b in beats if b["kind"] not in ("disclaimer", "disclosure"))
        if not (t["beats"]["min"] <= n <= t["beats"]["max"]):
            out.append(block("beat_count", "script.json", f"{n} {t['unit']}s; {lb['format']} allows {t['beats']['min']} to {t['beats']['max']}."))
        total = sum(len(b["text"].split()) for b in beats if b["kind"] not in ("disclaimer", "disclosure"))
        if total > t["max_words_total"]:
            out.append(block("too_long", "script.json", f"{total} words; limit {t['max_words_total']}.", "Cut, do not squeeze."))
        for b in beats:
            if b["kind"] not in ("disclaimer", "disclosure") and len(b["text"].split()) > t["max_words_per_beat"]:
                out.append(block("beat_long", b["id"], f"{len(b['text'].split())} words; limit {t['max_words_per_beat']}."))

    # --- coverage of every locked key point
    covered = {b.get("key_point") for b in beats if b["kind"] in ("point", "proof")}
    for kid in kps:
        if kid not in covered:
            out.append(block("key_point_missing", "script.json", f"Key point {kid} is never delivered.", "Add a point/proof beat for it."))

    banned = [x.lower() for x in comp.get("blocked_phrases", [])]
    advisory = [x.lower() for x in comp.get("advisory_terms", [])]
    triggers = [x.lower() for x in comp.get("performance_triggers", [])]
    generic = set(comp.get("entity_check", {}).get("generic_leading_words", []))
    allowed_entities = [e.lower() for e in lb["allowed_entities"]]
    oos = [x.lower() for x in lb["out_of_scope"]]
    req_stems = {stem(w) for term in lb["required_terms"] for w in re.findall(r"[a-z0-9]+", term.lower())}

    needs_disclaimer = False
    for b in beats:
        w, txt, low = b["id"], b["text"], b["text"].lower()

        if b["kind"] == "disclaimer":
            d = comp["disclaimers"].get(b.get("disclaimer_id", ""))
            if not d:
                out.append(block("unknown_disclaimer", w, "Disclaimer beat must name a disclaimer_id from compliance-rules.yaml."))
            elif not d["text"].strip():
                out.append(block("disclaimer_unfilled", w, "The compliance owner has not supplied this disclaimer's wording.",
                                 "Paste the official text into compliance-rules.yaml. Do not paraphrase."))
            elif squash(txt) != squash(d["text"]):
                out.append(block("disclaimer_altered", w, "Disclaimer text differs from the official wording on file.", "Use the text exactly."))
            continue
        if b["kind"] == "disclosure":
            if b["fact_ids"]:
                out.append(block("disclosure_with_facts", w, "The disclosure slide makes no claim and cites no fact."))
            continue

        # fact references must exist in the lock
        for fid in b["fact_ids"]:
            if fid not in facts:
                out.append(block("fact_not_locked", w, f"Cites {fid}, which is not in the locked brief.", "Use only locked facts."))
        if b["kind"] in ("point", "proof"):
            if not b.get("key_point") or b["key_point"] not in kps:
                out.append(block("unanchored", w, "A point/proof beat must carry a valid locked key_point."))
            if not b["fact_ids"]:
                out.append(block("no_fact", w, "A point/proof beat must cite at least one locked fact."))
            elif b.get("key_point") in kps:
                allowed = set(kps[b["key_point"]]["fact_ids"])
                stray = [f for f in b["fact_ids"] if f in facts and f not in allowed]
                if stray:
                    out.append(warn("fact_other_key_point", w, f"Cites {stray}, which back a different key point.", "Check it belongs here."))

        cited_text = " ".join(facts[f]["statement"] for f in b["fact_ids"] if f in facts).lower()
        cited_nums = set()
        for f in b["fact_ids"]:
            if f in facts:
                for n in facts[f].get("numbers", []):
                    v = norm_number(n["raw"].replace("%", "").replace("₹", "").strip())
                    if v is not None:
                        cited_nums.add(v)
                cited_nums.update(v for _, v in numbers_in(facts[f]["statement"], allow_labels=False))

        # --- every figure must come from a cited fact
        for raw, val in numbers_in(txt):
            if val not in cited_nums:
                out.append(block("unsupported_number", w, f"'{raw}' does not appear in any fact this beat cites.",
                                 "Remove it, or cite the approved fact that contains it."))
        for word in SPELLED_QTY:
            if re.search(r"\b" + word + r"\b", low) and word not in cited_text:
                out.append(block("unsupported_quantity", w, f"Spelled-out quantity '{word}' is not backed by a cited fact."))

        # --- banned and advisory language
        for ph in banned:
            if ph in low:
                out.append(block("banned_phrase", w, f"Contains '{ph}'.", "Remove or rewrite without the promise or superlative."))
        for ph in advisory:
            if re.search(r"\b" + re.escape(ph) + r"\b", low):
                out.append(warn("advisory_term", w, f"Contains '{ph}'. Check it can be substantiated."))

        # --- drift: out-of-scope terms are a hard stop
        for term in oos:
            if re.search(r"\b" + re.escape(term) + r"\b", low):
                out.append(block("out_of_scope", w, f"Mentions '{term}', which the approver excluded.", "Remove it; the brief does not cover it."))

        # --- topic anchoring
        stems = content_stems(txt)
        if b["kind"] in ("hook", "recap", "cta"):
            if b["kind"] != "cta" and not (stems & req_stems):
                out.append(block("hook_off_topic", w, f"A {b['kind']} beat must use at least one required term {lb['required_terms']}.",
                                 "Tie the opening/closing directly to the topic."))
        else:
            ref = set(req_stems)
            if b.get("key_point") in kps:
                ref |= content_stems(kps[b["key_point"]]["text"])
            ref |= content_stems(cited_text)
            shared = len(stems & ref)
            if shared == 0:
                out.append(block("drift", w, "Shares no substantive words with its key point or cited facts.", "Rewrite from the cited fact."))
            elif shared < 2:
                out.append(warn("possible_drift", w, "Shares only one substantive word with its key point and facts.", "Confirm it stays on the point."))

        # --- scheme / fund-house names must be approved
        for m in re.finditer(r"\b((?:[A-Z][\w&.\-]*\s+){1,4})(Mutual Fund|Fund|AMC|Asset Management)\b", txt):
            words = m.group(1).split()
            while words and words[0] in generic:
                words.pop(0)
            if words and words[-1] == "Mutual" and m.group(2) == "Fund":
                words.pop()          # "Many Mutual Fund investors": "Mutual" belongs to the phrase, not a name
            if not words:
                continue
            name = (" ".join(words) + " " + m.group(2)).lower()
            if not any(name in e or e in name for e in allowed_entities):
                out.append(block("unapproved_entity", w, f"Names '{name.title()}', which is not an allowed entity in the brief.",
                                 "Remove the name, or have the approver add it at Gate 3."))

        # --- performance claims
        if any(re.search(r"\b" + re.escape(tr) + r"\b", low) for tr in triggers) and numbers_in(txt):
            needs_disclaimer = True
            has_asof = any(n.get("as_of") for f in b["fact_ids"] if f in facts for n in facts[f].get("numbers", []))
            if not has_asof:
                out.append(block("claim_no_date", w, "A performance figure needs a cited fact that states the date it is as of."))

    if needs_disclaimer:
        if not any(b["kind"] == "disclaimer" and b.get("disclaimer_id") == "past_performance" for b in beats):
            out.append(block("disclaimer_missing", "script.json", "The script states a performance figure but has no past_performance disclaimer beat.",
                             "Add a disclaimer beat with disclaimer_id 'past_performance'."))
    return out


def check_semantic_review(run_dir: Path, **_):
    p = run_dir / "04_script" / "semantic_review.json"
    if not p.exists():
        return [block("missing_file", "semantic_review.json", "No independent review of the script yet.",
                      "Run the review pass in a fresh agent that has not seen the drafting.")]
    r = load_json(p)
    out = schema_findings("semantic_review", r, "semantic_review.json")
    if out:
        return out
    if not r["independent"]:
        out.append(block("not_independent", "semantic_review.json", "The reviewer must be independent of the drafter."))
    if r["script_sha256"] != sha256_file(run_dir / "04_script" / "script.json"):
        out.append(block("review_stale", "semantic_review.json", "The script changed after it was reviewed.", "Review again."))
    sc = load_json(run_dir / "04_script" / "script.json")
    reviewed = {b["id"]: b for b in r["beats"]}
    for b in sc["beats"]:
        if b["kind"] in ("disclaimer", "disclosure"):
            continue
        rb = reviewed.get(b["id"])
        if not rb:
            out.append(block("beat_unreviewed", b["id"], "Beat was not reviewed."))
        elif rb["verdict"] != "supported":
            out.append(block("review_" + rb["verdict"], b["id"], f"Reviewer says {rb['verdict']}: {rb['evidence']}", "Rewrite the beat and review again."))
    return out


# ------------------------------------------------------------------ step 5: design

def _lum(hexcol: str) -> float:
    c = hexcol.lstrip("#")
    rgb = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _bg_under(page: dict, l: dict) -> str:
    cx, cy = l["x"] + l["w"] / 2, l["y"] + min(l["h"], 10) / 2
    col = None
    for r in page["layers"]:
        if r["kind"] == "rect" and r.get("fill") not in (None, "none") and r["role"] not in ("progress", "rule"):
            if r["x"] <= cx <= r["x"] + r["w"] and r["y"] <= cy <= r["y"] + r["h"]:
                col = r["fill"]
    return col or "#FFFFFF"


def check_design_data(design: dict, script: dict, config_dir: Path, script_sha: str | None = None) -> list[Finding]:
    """Pure check of a design spec against the approved script. Used for engine runs and console runs."""
    out: list[Finding] = []
    brand = load_yaml(config_dir, "brand.yaml")
    slot = (load_yaml(config_dir, "compliance-rules.yaml").get("sebi_disclosure") or {}).get("slot_text", "")
    if str(brand.get("status", "")).startswith("placeholder"):
        out.append(warn("brand_placeholder", "brand.yaml", "Designs use the placeholder brand, not TheFinPedia's real assets.",
                        "Replace colours, fonts and the logo slot in config/brand.yaml, then rebuild."))
    if script_sha and design.get("script_sha256") != script_sha:
        out.append(block("design_stale", "design.json", "The script changed after the design was built.", "Rebuild the design."))
    if design.get("format") != script.get("format"):
        out.append(block("design_format", "design.json", f"Design format {design.get('format')} differs from script format {script.get('format')}."))
    cw, ch = design["canvas"]["w"], design["canvas"]["h"]
    if brand["canvas"].get(design["format"]) != design["canvas"]:
        out.append(block("design_canvas", "design.json", "Page size does not match brand.yaml for this format.", "Rebuild the design."))
    m = int(min(cw, ch) * brand["margin"])
    beats = {b["id"]: b for b in script["beats"]}
    content_ids = [b["id"] for b in script["beats"] if b["kind"] != "disclosure"]
    placed = [bid for p in design["pages"] for bid in p["beat_ids"]]
    if placed != content_ids:
        out.append(block("design_order", "design.json", f"Pages carry beats {placed}, the script has {content_ids} in that order.",
                         "Every beat must appear once, in script order."))
    disclosure = next((b for b in script["beats"] if b["kind"] == "disclosure"), None)
    for i, p in enumerate(design["pages"]):
        w = p["id"]
        texts = [l for l in p["layers"] if l["kind"] == "text"]
        for l in texts:
            where = f"{w}/{l['id']}"
            if l["role"] == "script":
                b = beats.get(l.get("beat_id"))
                if not b or l["text"] != b["text"]:
                    out.append(block("design_text_changed", where, "Text on the page is not word-for-word the approved beat.",
                                     "Never edit words in design. Change the script and get Gate 4 again."))
                elif " ".join(l.get("lines", [])) != " ".join(b["text"].split()):
                    out.append(block("design_wrap_lost_words", where, "Wrapped lines do not add up to the beat text."))
            elif l["role"] == "highlight":
                b = beats.get(l.get("beat_id"))
                if not b or l["text"] not in b["text"] or l.get("beat_id") not in p["beat_ids"]:
                    out.append(block("design_highlight_not_in_beat", where, f"Highlighted figure '{l['text']}' is not in this page's beat."))
            elif l["role"] == "disclosure":
                if l["text"] != slot or (disclosure and l["text"] != disclosure["text"]):
                    out.append(block("design_disclosure_altered", where, "SEBI disclosure text must be the placeholder text exactly.",
                                     "Real names and numbers are filled at co-branding, never in design."))
            else:
                out.append(block("design_extra_text", where, f"Text layer with role '{l['role']}' is not allowed. Only script, highlight and disclosure text may appear."))
            if l["x"] < m - 1 or l["x"] + l["w"] > cw - m + 1 or l["y"] < 0 or l["y"] + l["h"] > ch:
                out.append(block("design_outside_safe_area", where, "Text runs outside the page's safe area.", "Shorten the beat in the script or use a smaller layout."))
            bg = _bg_under(p, l)
            if contrast(l["color"], bg) < brand["min_contrast"]:
                out.append(block("design_low_contrast", where, f"Contrast {contrast(l['color'], bg):.1f}:1 is below {brand['min_contrast']}:1."))
            if l["font_size"] < 20 and l["role"] != "disclosure":
                out.append(warn("design_small_text", where, f"Font size {l['font_size']} px may be hard to read on a phone."))
        script_layers = [l for l in texts if l["role"] == "script"]
        for a_i, a in enumerate(script_layers):
            for b2 in script_layers[a_i + 1:] + [l for l in texts if l["role"] != "script"]:
                if a["x"] < b2["x"] + b2["w"] and b2["x"] < a["x"] + a["w"] and a["y"] < b2["y"] + b2["h"] and b2["y"] < a["y"] + a["h"]:
                    out.append(block("design_overlap", f"{w}/{a['id']}", f"Text overlaps {b2['id']}.", "Shorten the beat or rebuild with another layout."))
        has_disc = any(l["role"] == "disclosure" for l in texts)
        need = disclosure is not None and (brand["disclosure_placement"] == "every_page" or i == 0)
        if need and not has_disc:
            out.append(block("design_disclosure_missing", w, "SEBI disclosure strip is missing on this page."))
        if not any(l["role"] == "logo_slot" for l in p["layers"]):
            out.append(warn("design_no_logo_slot", w, "No distributor logo slot on this page."))
    if disclosure is None:
        out.append(block("design_no_disclosure_beat", "script.json", "The script has no SEBI disclosure beat, so the design cannot carry it.",
                         "Reopen step 4 and add the disclosure beat."))
    return out


def check_design(run_dir: Path, config_dir: Path, **_):
    d = run_dir / "05_design" / "design.json"
    if not (run_dir / "handoff.json").exists():
        return [block("no_handoff", "handoff.json", "Step 4 is not complete, so design cannot start.")]
    if not d.exists():
        return [block("missing", "05_design/design.json", "No design yet.", "Run: python3 tools/design.py build <run>")]
    sp = run_dir / "04_script" / "script.json"
    out = check_design_data(load_json(d), load_json(sp), config_dir, sha256_file(sp))
    f = run_dir / "05_design" / "fabric.json"
    if not f.exists():
        out.append(block("missing", "05_design/fabric.json", "No Fabric.js export.", "Rebuild the design."))
    return out


# ------------------------------------------------------------------ step 6: video

def check_video_data(man: dict, design: dict, config_dir: Path, design_sha: str | None = None, mp4_path: Path | None = None) -> list[Finding]:
    out: list[Finding] = []
    brand = load_yaml(config_dir, "brand.yaml")
    vid = brand["video"]
    slot = (load_yaml(config_dir, "compliance-rules.yaml").get("sebi_disclosure") or {}).get("slot_text", "")
    if design_sha and man.get("design_sha256") != design_sha:
        out.append(block("video_stale", "video.json", "The design changed after the video was rendered.", "Render again."))
    if mp4_path is not None:
        if not mp4_path.exists():
            out.append(block("video_missing", "video.mp4", "No rendered video.", "Run: python3 tools/animate.py build <run>"))
        elif man.get("mp4_sha256") != sha256_file(mp4_path):
            out.append(block("video_changed", "video.mp4", "The MP4 is not the file this manifest describes (edited or re-rendered outside the engine)."))
    sc = man.get("scenes", [])
    if not sc or sc[0]["kind"] != "slate" or [t["text"] for t in sc[0]["texts"]] != [slot]:
        out.append(block("video_no_disclosure_slate", "video.json", "The video must open with the SEBI disclosure slate, placeholder text unchanged."))
    elif sc[0]["frames"] < vid["disclosure_seconds"] * man["fps"]:
        out.append(block("video_slate_short", "S00", f"Disclosure slate is shorter than {vid['disclosure_seconds']} s."))
    pages = [s for s in sc if s["kind"] == "page"]
    if [s["page_id"] for s in pages] != [p["id"] for p in design["pages"]]:
        out.append(block("video_pages", "video.json", "Scenes do not match the approved design pages one to one, in order."))
    by_id = {p["id"]: p for p in design["pages"]}
    for s in pages:
        p = by_id.get(s["page_id"])
        if not p:
            continue
        want = [{"role": l["role"], "text": l["text"]} for l in p["layers"] if l["kind"] == "text"]
        if s["texts"] != want:
            out.append(block("video_text_changed", s["id"], "Words in this scene differ from the approved design page."))
        n = sum(len(t["text"].split()) for t in s["texts"] if t["role"] in ("script", "highlight"))
        need = min(max(n * vid["seconds_per_word"], vid["min_scene_seconds"]), vid["max_scene_seconds"])
        if s["frames"] + 1 < need * man["fps"]:
            out.append(block("video_too_fast", s["id"], f"{n} words on screen for {s['frames'] / man['fps']:.1f} s; needs {need:.1f} s to read."))
        if n * vid["seconds_per_word"] > vid["max_scene_seconds"]:
            out.append(warn("video_dense", s["id"], f"{n} words may be too many to read in {vid['max_scene_seconds']} s.", "Consider a shorter beat."))
    if (man.get("width"), man.get("height")) != (design["canvas"]["w"], design["canvas"]["h"]):
        out.append(block("video_size", "video.json", "Video size differs from the approved design."))
    out.append(warn("video_no_audio", "video.mp4", "The video has no voice-over or music yet.", "Add licensed music or a voice-over before publishing; record its source."))
    return out


def check_video(run_dir: Path, config_dir: Path, **_):
    d, m = run_dir / "05_design" / "design.json", run_dir / "06_animation" / "video.json"
    if not m.exists():
        return [block("missing", "06_animation/video.json", "No video yet.", "Run: python3 tools/animate.py build <run>")]
    return check_video_data(load_json(m), load_json(d), config_dir, sha256_file(d), run_dir / "06_animation" / "video.mp4")


# ------------------------------------------------------------------ short reels (card based)

def check_reel_cards(reel: dict, facts: dict, config_dir: Path) -> list[Finding]:
    """reel: {cards: [{big?, line, small?, fact_ids?}], cuts: [...frames], frames, fps?, slot};
    facts: {fact_id: fact dict with statement/nums/excerpt}. Numbers on every card must be in that card's cited facts."""
    out: list[Finding] = []
    t = load_yaml(config_dir, "content-types.yaml")["types"]["reels_short"]
    fps = reel.get("fps", 30)
    slot = (load_yaml(config_dir, "compliance-rules.yaml").get("sebi_disclosure") or {}).get("slot_text", "")
    if reel.get("slot") != slot:
        out.append(block("reel_disclosure_altered", "slot", "The disclosure strip must carry the placeholder text exactly."))
    secs = reel["frames"] / fps
    if secs > t["max_seconds"]:
        out.append(block("reel_too_long", "frames", f"{secs:.1f} s is over {t['max_seconds']} s."))
    cards = reel["cards"]
    if not t["beats"]["min"] <= len(cards) <= t["beats"]["max"]:
        out.append(block("reel_card_count", "cards", f"{len(cards)} cards; allowed {t['beats']['min']} to {t['beats']['max']}."))
    edges = [0] + list(reel["cuts"]) + [reel["frames"]]
    total = 0
    for i, c in enumerate(cards):
        words = " ".join(x for x in (c.get("big"), c.get("line"), c.get("small")) if x)
        n = len(words.split()); total += n
        dur = (edges[i + 1] - edges[i]) / fps
        if dur + 1e-6 < n * t["seconds_per_word"]:
            out.append(block("reel_card_too_fast", f"card {i + 1}", f"{n} words for {dur:.1f} s; needs {n * t['seconds_per_word']:.1f} s."))
        if n > t["max_words_per_beat"] + 3:
            out.append(warn("reel_card_wordy", f"card {i + 1}", f"{n} words on one card."))
        pool = " ".join((facts[f].get("statement", "") + " " + " ".join(facts[f].get("nums", [])) + " " + facts[f].get("excerpt", "")) for f in c.get("fact_ids", []) if f in facts).replace(",", "")
        for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", words):
            k = raw.rstrip(",").replace(",", "")
            if not re.search(r"(^|[^\d.])" + re.escape(k) + r"([^\d]|\.(?!\d)|$)", pool):
                out.append(block("reel_number_not_in_fact", f"card {i + 1}", f"Number {raw} is not in a cited fact."))
    if total > t["max_words_total"]:
        out.append(block("reel_too_many_words", "cards", f"{total} on-screen words; limit {t['max_words_total']}."))
    return out


CHECKS = {
    "topic": check_topic,
    "ledger": lambda **k: check_ledger(final=False, **k),
    "ledger_final": lambda **k: check_ledger(final=True, **k),
    "angles": lambda **k: check_angles(need_selection=False, **k),
    "angles_selected": lambda **k: check_angles(need_selection=True, **k),
    "lock": check_lock,
    "storyline": check_storyline,
    "script": check_script,
    "semantic_review": check_semantic_review,
    "design": check_design,
    "video": check_video,
}
