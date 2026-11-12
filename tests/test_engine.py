"""Tests for steps 1-4. All data here is FIXTURE data (invented) used only to prove the guards work.

Run:  python3 -I -m unittest discover -s tests -v      (from the project folder)
"""
import contextlib
import copy
import datetime as dt
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import engine  # noqa: E402
import validators as V  # noqa: E402
import yaml  # noqa: E402

TODAY = dt.date.today()
D = lambda n: (TODAY - dt.timedelta(days=n)).isoformat()          # noqa: E731
LONG = lambda n: (TODAY - dt.timedelta(days=n)).strftime("%d %B %Y").lstrip("0")  # noqa: E731
FIXTURE_DISCLAIMER = "FIXTURE ONLY disclaimer wording supplied by a test, not real compliance text."


def fact(i, statement, publisher, url, excerpt, numbers=None, tier="tier1", status="approved"):
    return {"id": f"F{i:03d}", "statement": statement, "numbers": numbers or [],
            "source": {"tier": tier, "publisher": publisher, "title": "FIXTURE page", "url": url, "accessed": D(1)},
            "evidence_excerpt": excerpt, "status": status, "added_by": "ai", "reviewed_by": "Rita Researcher"}


LEDGER = {"facts": [
    fact(1, "A systematic investment plan lets an investor put a fixed amount into a mutual fund scheme at regular intervals.",
         "AMFI", "https://www.amfiindia.com/fixture/sip", "invest a fixed amount at regular intervals"),
    fact(2, "Fixture instalment example of 1234 rupees per month, used only in tests.", "AMFI", "https://www.amfiindia.com/fixture/amt",
         "fixture example instalment", [{"raw": "1234", "as_of": D(5)}]),
    fact(3, "Units are allotted at the prevailing net asset value on each instalment date, so a fixed amount buys more units when the NAV is lower.",
         "SEBI", "https://www.sebi.gov.in/fixture/nav", "units are allotted at the prevailing NAV"),
    fact(4, "An investor can usually pause or stop a systematic investment plan by giving the fund house notice.",
         "AMFI", "https://www.amfiindia.com/fixture/stop", "pause or stop by giving notice"),
    fact(5, f"Fixture scheme returned 9.5% CAGR over 5 years as of {LONG(10)}.", "SEBI", "https://www.sebi.gov.in/fixture/perf",
         "fixture performance excerpt", [{"raw": "9.5%", "as_of": D(10)}, {"raw": "5", "as_of": D(10)}]),
]}

TOPIC = {"topic": "How a SIP works for first-time investors", "mode": "topic_driven", "picked_by": "Rita Researcher", "picked_on": D(0),
         "scope_notes": "Explain the mechanism only. No product recommendations or tax discussion."}


def angle(aid, fmt, kps):
    return {"id": aid, "title": f"Angle {aid}", "core_message": "A SIP builds an investing habit by buying a fixed amount at regular intervals.",
            "key_points": kps, "audience": "First-time investors", "format": fmt, "why_now": "Evergreen basics.",
            "required_terms": ["SIP", "fixed amount"], "out_of_scope": ["tax", "crypto", "lumpsum"], "allowed_entities": [], "risks": []}


KPS = [{"id": "K1", "text": "A SIP invests a fixed amount at regular intervals", "fact_ids": ["F001", "F002", "F005"]},
       {"id": "K2", "text": "Units are allotted at NAV, so a lower NAV buys more units", "fact_ids": ["F003"]},
       {"id": "K3", "text": "An investor can pause or stop a SIP with notice", "fact_ids": ["F004"]}]
ANGLES = {"angles": [angle("A1", "carousel", KPS), angle("A2", "reels", KPS), angle("A3", "minimalist", KPS[:1])]}

BEATS = [
    ("B01", "hook", None, [], "What does a SIP actually do for you?"),
    ("B02", "point", "K1", ["F001"], "A SIP puts a fixed amount into a mutual fund scheme at regular intervals."),
    ("B03", "proof", "K1", ["F001"], "Think of it as a standing instruction: the same fixed amount, on a schedule."),
    ("B04", "point", "K2", ["F003"], "Units are allotted at the prevailing NAV on each instalment date, so a fixed amount buys more units when NAV is lower."),
    ("B05", "proof", "K2", ["F003"], "Lower NAV, more units for the same fixed amount."),
    ("B06", "point", "K3", ["F004"], "An investor can usually pause or stop a SIP by giving the fund house notice."),
    ("B07", "recap", None, [], "A SIP means a fixed amount, invested at regular intervals."),
    ("B08", "cta", None, [], "Save this post to revisit how a SIP works."),
]


def script_from(beats, lock_hash, core="A SIP builds an investing habit by buying a fixed amount at regular intervals.", fmt="carousel"):
    return {"core_message": core, "locked_brief_sha256": lock_hash, "format": fmt,
            "beats": [{"id": i, "kind": k, "text": t, "key_point": kp, "fact_ids": f} for i, k, kp, f, t in beats]}


def codes(findings, level="block"):
    return {f.code for f in findings if f.level == level}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.conf = self.tmp / "config"
        shutil.copytree(ROOT / "config", self.conf)
        ap = yaml.safe_load((self.conf / "approvers.yaml").read_text())
        ap["roles"] = {"researcher": ["Rita Researcher"], "content_lead": ["Cara Lead"], "topic_approver": ["Tom Approver"]}
        (self.conf / "approvers.yaml").write_text(yaml.safe_dump(ap))
        # Most tests are about other rules, so the SEBI slot is switched off here and tested in DisclosureSlot.
        cr = yaml.safe_load((self.conf / "compliance-rules.yaml").read_text())
        cr["sebi_disclosure"]["required"] = False
        (self.conf / "compliance-rules.yaml").write_text(yaml.safe_dump(cr, allow_unicode=True))
        self.runs = self.tmp / "runs"
        self.runs.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cli(self, *args, expect=0):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = engine.main(["--runs-dir", str(self.runs), "--config-dir", str(self.conf), *args])
        self.assertEqual(rc, expect, f"{args}\nSTDOUT:{out.getvalue()}\nSTDERR:{err.getvalue()}")
        return out.getvalue() + err.getvalue()

    def write(self, rel, data):
        p = self.rd / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def start(self):
        self.cli("new", "--topic", "How a SIP works", "--by", "Rita Researcher")
        self.run_id = next(self.runs.iterdir()).name
        self.rd = self.runs / self.run_id

    def to_step4(self, beats=BEATS):
        """Drive a run through gates 1-3 with named humans, then write step 4 files."""
        self.start()
        self.write("01_research/topic.json", TOPIC)
        ledger = copy.deepcopy(LEDGER)
        for f in ledger["facts"]:
            f["status"], f.pop("reviewed_by", None)
            f["status"] = "proposed"
        self.write("01_research/fact_ledger.json", ledger)
        self.cli("facts", self.run_id, "--by", "Rita Researcher", "--approve", "F001,F002,F003,F004,F005")
        self.cli("approve", self.run_id, "G1", "--by", "Rita Researcher", "--decision", "approve")
        self.cli("advance", self.run_id)
        self.write("02_ideation/angles.json", ANGLES)
        self.cli("select", self.run_id, "--angle", "A1", "--by", "Cara Lead")
        self.cli("approve", self.run_id, "G2", "--by", "Cara Lead", "--decision", "approve")
        self.cli("advance", self.run_id)
        self.cli("lock", self.run_id)
        self.cli("approve", self.run_id, "G3", "--by", "Tom Approver", "--decision", "approve")
        self.cli("advance", self.run_id)
        self.lock_hash = V.sha256_file(self.rd / "03_approval" / "locked_brief.json")
        self.write("04_script/storyline.json", {"core_message": "A SIP builds an investing habit by buying a fixed amount at regular intervals.",
            "locked_brief_sha256": self.lock_hash, "arc": [
                {"act": "hook", "purpose": "Open on the topic", "key_point": None},
                {"act": "point", "purpose": "Say what a SIP is", "key_point": "K1"},
                {"act": "proof", "purpose": "Make K1 concrete", "key_point": "K1"},
                {"act": "point", "purpose": "Explain NAV and units", "key_point": "K2"},
                {"act": "proof", "purpose": "Show lower NAV effect", "key_point": "K2"},
                {"act": "point", "purpose": "Say you can stop", "key_point": "K3"},
                {"act": "recap", "purpose": "Restate message", "key_point": None},
                {"act": "cta", "purpose": "Ask to save", "key_point": None}]})
        self.write_script(beats)

    def write_script(self, beats, **kw):
        self.write("04_script/script.json", script_from(beats, self.lock_hash, **kw))

    def script_findings(self):
        return V.check_script(run_dir=self.rd, config_dir=self.conf)

    def review(self, verdicts=None):
        sc = V.load_json(self.rd / "04_script" / "script.json")
        verdicts = verdicts or {}
        self.write("04_script/semantic_review.json", {"reviewer": "fresh-agent", "independent": True,
            "script_sha256": V.sha256_file(self.rd / "04_script" / "script.json"),
            "beats": [{"id": b["id"], "verdict": verdicts.get(b["id"], "supported"), "evidence": "Matches cited fact wording closely."}
                      for b in sc["beats"] if b["kind"] not in ("disclaimer", "disclosure")]})


class ShippedConfig(unittest.TestCase):
    def test_shipped_approvers_and_sources_work(self):
        ap = yaml.safe_load((ROOT / "config" / "approvers.yaml").read_text())["roles"]
        self.assertEqual(ap["topic_approver"], ["Ratnesh"])
        self.assertIn("Milind", ap["researcher"])
        src = yaml.safe_load((ROOT / "config" / "research-sources.yaml").read_text())
        self.assertEqual(V._domain_tier("https://dummy-amc.example.com/x", src), "tier2")
        comp = yaml.safe_load((ROOT / "config" / "compliance-rules.yaml").read_text())
        self.assertTrue(comp["disclaimers"]["past_performance"]["text"].startswith("DUMMY"))


class HappyPath(Base):
    def test_full_run_steps_1_to_4(self):
        self.to_step4()
        self.assertEqual(codes(self.script_findings()), set(), [f.as_dict() for f in self.script_findings()])
        self.assertEqual(V.check_storyline(run_dir=self.rd), [])
        self.review()
        self.cli("approve", self.run_id, "G4", "--by", "Cara Lead", "--decision", "approve")
        self.cli("advance", self.run_id)
        h = json.loads((self.rd / "handoff.json").read_text())
        self.assertEqual(h["format"], "carousel")
        self.assertTrue(any(a["gate"] == "G4" for a in h["approvals"]))
        self.cli("verify-log", self.run_id)


class Gates(Base):
    def test_unlisted_person_cannot_approve(self):
        self.to_step4()
        self.review()
        out = self.cli("approve", self.run_id, "G4", "--by", "Rita Researcher", "--decision", "approve", expect=2)
        self.assertIn("not allowed", out)

    def test_empty_approver_list_refuses(self):
        (self.conf / "approvers.yaml").write_text("roles: {researcher: [], content_lead: [], topic_approver: []}\n")
        self.start()
        out = self.cli("facts", self.run_id, "--by", "Anyone", "--approve", "F001", expect=2)
        self.assertIn("No one is listed", out)

    def test_cannot_advance_without_approval(self):
        self.start()
        out = self.cli("advance", self.run_id, expect=2)
        self.assertIn("no standing approval", out)

    def test_edit_after_approval_invalidates_it(self):
        self.to_step4()
        self.review()
        self.cli("approve", self.run_id, "G4", "--by", "Cara Lead", "--decision", "approve")
        sc = V.load_json(self.rd / "04_script" / "script.json")
        sc["beats"][1]["text"] += " Extra words added later."
        self.write("04_script/script.json", sc)
        out = self.cli("advance", self.run_id, expect=2)
        self.assertIn("Files changed after", out)

    def test_gate_refuses_while_blocking_findings(self):
        self.to_step4()
        self.review()
        sc = V.load_json(self.rd / "04_script" / "script.json")
        sc["beats"][1]["text"] = "A SIP is guaranteed to grow your money at regular intervals."
        self.write("04_script/script.json", sc)
        self.review()
        out = self.cli("approve", self.run_id, "G4", "--by", "Cara Lead", "--decision", "approve", expect=2)
        self.assertIn("blocking findings remain", out)

    def test_reject_needs_note(self):
        self.to_step4()
        self.cli("approve", self.run_id, "G4", "--by", "Cara Lead", "--decision", "reject", expect=2)

    def test_log_tamper_detected(self):
        self.to_step4()
        lp = self.rd / "approvals.jsonl"
        lines = lp.read_text().splitlines()
        e = json.loads(lines[0])
        e["by"] = "Someone Else"
        lines[0] = json.dumps(e)
        lp.write_text("\n".join(lines) + "\n")
        out = self.cli("verify-log", self.run_id, expect=1)
        self.assertIn("altered", out)

    def test_separation_of_duties(self):
        ap = yaml.safe_load((self.conf / "approvers.yaml").read_text())
        ap["roles"]["content_lead"] = ["Cara Lead", "Tom Approver"]
        ap["separation_of_duties"]["gate4_differs_from_gate3"] = True
        (self.conf / "approvers.yaml").write_text(yaml.safe_dump(ap))
        self.to_step4()
        self.review()
        out = self.cli("approve", self.run_id, "G4", "--by", "Tom Approver", "--decision", "approve", expect=2)
        self.assertIn("Separation of duties", out)


class MissingFiles(Base):
    def test_missing_file_gives_clear_refusal_not_crash(self):
        self.start()
        out = self.cli("facts", self.run_id, "--by", "Rita Researcher", "--approve", "F001", expect=2)
        self.assertIn("has not been written yet", out)


class Reopen(Base):
    def test_failure_returns_to_causing_step_and_is_logged(self):
        self.to_step4()
        self.review()
        self.cli("reopen", self.run_id, "--step", "1", "--by", "Cara Lead", "--note", "Fact F003 wording was wrong")
        self.assertEqual(json.loads((self.rd / "state.json").read_text())["step"], 1)
        self.assertTrue(any(e["decision"] == "reopened" for e in engine.read_log(self.rd)))
        self.cli("reopen", self.run_id, "--step", "3", "--by", "Cara Lead", "--note", "x", expect=2)   # cannot jump forward
        self.cli("reopen", self.run_id, "--step", "1", "--by", "Nobody", "--note", "x", expect=2)      # unlisted person

    def test_changed_research_makes_lock_stale(self):
        self.to_step4()
        led = V.load_json(self.rd / "01_research" / "fact_ledger.json")
        led["facts"][0]["review_note"] = "edited after lock"
        self.write("01_research/fact_ledger.json", led)
        self.assertIn("lock_stale", codes(V.check_lock(run_dir=self.rd, config_dir=self.conf)))


class ResearchGuards(Base):
    def ledger_with(self, mutate):
        if not hasattr(self, "rd"):
            self.start()
        led = copy.deepcopy(LEDGER)
        mutate(led)
        self.write("01_research/topic.json", TOPIC)
        self.write("01_research/fact_ledger.json", led)
        return V.check_ledger(run_dir=self.rd, config_dir=self.conf, final=True)

    def test_clean_ledger_passes(self):
        self.assertEqual(codes(self.ledger_with(lambda l: None)), set())

    def test_media_source_cannot_back_a_fact(self):
        def m(l):
            l["facts"][0]["source"]["url"] = "https://www.livemint.com/fixture"
            l["facts"][0]["source"]["tier"] = "tier3"
        self.assertIn("lead_only_source", codes(self.ledger_with(m)))

    def test_unknown_domain_blocked(self):
        def m(l): l["facts"][0]["source"]["url"] = "https://random-blog.example/post"
        self.assertIn("source_not_allowed", codes(self.ledger_with(m)))

    def test_missing_evidence_blocked(self):
        def m(l): l["facts"][0]["evidence_excerpt"] = ""
        self.assertIn("no_evidence", codes(self.ledger_with(m)))

    def test_undeclared_figure_blocked(self):
        def m(l): l["facts"][0]["statement"] += " The minimum is 500 rupees."
        self.assertIn("undeclared_number", codes(self.ledger_with(m)))

    def test_figure_without_date_blocked(self):
        def m(l): l["facts"][1]["numbers"] = [{"raw": "1234"}]
        self.assertIn("schema", codes(self.ledger_with(m)) | {"schema"})

    def test_stale_figure_blocked_unless_human_accepts(self):
        def m(l): l["facts"][1]["numbers"][0]["as_of"] = D(400)
        self.assertIn("stale_figure", codes(self.ledger_with(m)))
        def m2(l):
            l["facts"][1]["numbers"][0]["as_of"] = D(400)
            l["facts"][1]["review_note"] = "Reviewed: figure unchanged since."
        self.assertNotIn("stale_figure", codes(self.ledger_with(m2)))

    def test_undecided_fact_blocks_gate(self):
        def m(l): l["facts"][2]["status"] = "proposed"
        self.assertIn("undecided", codes(self.ledger_with(m)))

    def test_open_conflict_blocks_gate(self):
        def m(l): l["conflicts"] = [{"fact_ids": ["F001", "F004"], "description": "Sources disagree on wording."}]
        self.assertIn("conflict_open", codes(self.ledger_with(m)))

    def test_too_thin_blocks_gate(self):
        def m(l):
            for f in l["facts"][2:]: f["status"] = "rejected"
        self.assertIn("too_thin", codes(self.ledger_with(m)))


class IdeationGuards(Base):
    def angles_with(self, mutate, need=False):
        self.to_step4()
        a = copy.deepcopy(ANGLES)
        mutate(a)
        self.write("02_ideation/angles.json", a)
        return V.check_angles(run_dir=self.rd, config_dir=self.conf, need_selection=need)

    def test_not_a_platform_type(self):
        def m(a): a["angles"][0]["format"] = "tiktok_dance"
        self.assertIn("bad_format", codes(self.angles_with(m)))

    def test_cites_unapproved_fact(self):
        def m(a): a["angles"][0]["key_points"][0]["fact_ids"] = ["F099"]
        self.assertIn("unapproved_fact", codes(self.angles_with(m)))

    def test_long_message(self):
        def m(a): a["angles"][0]["core_message"] = " ".join(["word"] * 31)
        self.assertIn("message_long", codes(self.angles_with(m)))

    def test_selection_required_for_gate(self):
        def m(a): pass
        self.assertIn("no_selection", codes(self.angles_with(m, need=True)))


class ScriptGuards(Base):
    def with_beat(self, i, **changes):
        self.to_step4()
        beats = [list(b) for b in BEATS]
        idx = int(i[1:]) - 1
        keys = ["id", "kind", "key_point", "fact_ids", "text"]
        for k, v in changes.items():
            beats[idx][keys.index(k)] = v
        self.write_script([tuple(b) for b in beats])
        return self.script_findings()

    def test_unsupported_number(self):
        f = self.with_beat("B02", text="A SIP puts a fixed amount, even 500 rupees, into a mutual fund scheme.")
        self.assertIn("unsupported_number", codes(f))

    def test_supported_number_passes(self):
        f = self.with_beat("B03", text="Say the fixed amount is 1234 rupees each month.", fact_ids=["F001", "F002"])
        self.assertNotIn("unsupported_number", codes(f))

    def test_spelled_out_quantity(self):
        f = self.with_beat("B03", text="A SIP can grow your fixed amount by twenty percent.")
        self.assertIn("unsupported_quantity", codes(f))

    def test_banned_phrase(self):
        f = self.with_beat("B02", text="A SIP is guaranteed to grow your fixed amount.")
        self.assertIn("banned_phrase", codes(f))

    def test_out_of_scope_term(self):
        f = self.with_beat("B04", text="Units are allotted at NAV and a fixed amount may help with tax planning.")
        self.assertIn("out_of_scope", codes(f))

    def test_drift_off_topic_beat(self):
        f = self.with_beat("B05", text="Weather forecasts improve with better satellites.")
        self.assertIn("drift", codes(f))

    def test_off_topic_hook(self):
        f = self.with_beat("B01", text="Ever wondered how your money grows overnight?")
        self.assertIn("hook_off_topic", codes(f))

    def test_message_reworded(self):
        self.to_step4()
        self.write_script(BEATS, core="A SIP is a smart way to grow wealth.")
        self.assertIn("message_changed", codes(self.script_findings()))

    def test_unapproved_scheme_name(self):
        f = self.with_beat("B03", text="Acme Growth Mutual Fund shows the same fixed amount idea.")
        self.assertIn("unapproved_entity", codes(f))

    def test_generic_mutual_fund_phrase_allowed(self):
        f = self.with_beat("B03", text="Many Mutual Fund investors use a fixed amount each month.")
        self.assertNotIn("unapproved_entity", codes(f))

    def test_uncited_fact_blocked(self):
        f = self.with_beat("B02", fact_ids=[])
        self.assertIn("no_fact", codes(f))

    def test_fact_outside_lock_blocked(self):
        f = self.with_beat("B02", fact_ids=["F099"])
        self.assertIn("fact_not_locked", codes(f))

    def test_missing_key_point_blocked(self):
        self.to_step4([b for b in BEATS if b[2] != "K3"])
        self.assertIn("key_point_missing", codes(self.script_findings()))

    def test_performance_claim_needs_disclaimer(self):
        f = self.with_beat("B03", text="The fixture scheme returned 9.5% CAGR over 5 years in a SIP.", fact_ids=["F005"])
        self.assertIn("disclaimer_missing", codes(f))

    def test_disclaimer_unfilled_blocks(self):
        cfg = yaml.safe_load((self.conf / "compliance-rules.yaml").read_text())
        cfg["disclaimers"]["past_performance"]["text"] = ""
        (self.conf / "compliance-rules.yaml").write_text(yaml.safe_dump(cfg))
        self.to_step4()
        beats = [list(b) for b in BEATS]
        beats[2][4] = "The fixture scheme returned 9.5% CAGR over 5 years in a SIP."
        beats[2][3] = ["F005"]
        sc = script_from([tuple(b) for b in beats], self.lock_hash)
        sc["beats"].append({"id": "B09", "kind": "disclaimer", "text": "anything", "fact_ids": [], "disclaimer_id": "past_performance"})
        self.write("04_script/script.json", sc)
        self.assertIn("disclaimer_unfilled", codes(self.script_findings()))

    def test_disclaimer_exact_text_passes_and_altered_fails(self):
        cfg = yaml.safe_load((self.conf / "compliance-rules.yaml").read_text())
        cfg["disclaimers"]["past_performance"]["text"] = FIXTURE_DISCLAIMER
        (self.conf / "compliance-rules.yaml").write_text(yaml.safe_dump(cfg))
        self.to_step4()
        beats = [list(b) for b in BEATS]
        beats[2][4] = "The fixture scheme returned 9.5% CAGR over 5 years in a SIP."
        beats[2][3] = ["F005"]
        sc = script_from([tuple(b) for b in beats], self.lock_hash)
        sc["beats"].append({"id": "B09", "kind": "disclaimer", "text": FIXTURE_DISCLAIMER, "fact_ids": [], "disclaimer_id": "past_performance"})
        self.write("04_script/script.json", sc)
        self.assertEqual(codes(self.script_findings()), set(), [f.as_dict() for f in self.script_findings()])
        sc["beats"][-1]["text"] = FIXTURE_DISCLAIMER + " Plus a friendly reworded bit."
        self.write("04_script/script.json", sc)
        self.assertIn("disclaimer_altered", codes(self.script_findings()))

    def test_script_too_long_for_format(self):
        f = self.with_beat("B04", text="Units are allotted at the prevailing NAV on each instalment date " * 4 + "so a fixed amount buys more units")
        self.assertTrue({"beat_long", "too_long"} & codes(f))

    def test_script_against_wrong_lock(self):
        self.to_step4()
        sc = script_from(BEATS, "0" * 64)
        self.write("04_script/script.json", sc)
        self.assertIn("wrong_lock", codes(self.script_findings()))


class SemanticReviewGuards(Base):
    def test_off_topic_verdict_blocks(self):
        self.to_step4()
        self.review({"B05": "off_topic"})
        self.assertIn("review_off_topic", codes(V.check_semantic_review(run_dir=self.rd)))

    def test_stale_review_blocks(self):
        self.to_step4()
        self.review()
        sc = V.load_json(self.rd / "04_script" / "script.json")
        sc["beats"][0]["text"] = "What does a SIP really do for you?"
        self.write("04_script/script.json", sc)
        self.assertIn("review_stale", codes(V.check_semantic_review(run_dir=self.rd)))

    def test_unreviewed_beat_blocks(self):
        self.to_step4()
        self.review()
        r = V.load_json(self.rd / "04_script" / "semantic_review.json")
        r["beats"] = r["beats"][:-1]
        self.write("04_script/semantic_review.json", r)
        self.assertIn("beat_unreviewed", codes(V.check_semantic_review(run_dir=self.rd)))

    def test_non_independent_review_blocks(self):
        self.to_step4()
        self.review()
        r = V.load_json(self.rd / "04_script" / "semantic_review.json")
        r["independent"] = False
        self.write("04_script/semantic_review.json", r)
        self.assertIn("not_independent", codes(V.check_semantic_review(run_dir=self.rd)))


class StorylineGuards(Base):
    def test_storyline_missing_key_point(self):
        self.to_step4()
        s = V.load_json(self.rd / "04_script" / "storyline.json")
        s["arc"] = [a for a in s["arc"] if a["key_point"] != "K3"]
        self.write("04_script/storyline.json", s)
        self.assertIn("key_point_missing", codes(V.check_storyline(run_dir=self.rd)))

    def test_storyline_must_open_with_hook(self):
        self.to_step4()
        s = V.load_json(self.rd / "04_script" / "storyline.json")
        s["arc"] = s["arc"][1:]
        self.write("04_script/storyline.json", s)
        self.assertIn("arc_start", codes(V.check_storyline(run_dir=self.rd)))


class DisclosureSlot(Base):
    def setUp(self):
        super().setUp()
        cr = yaml.safe_load((self.conf / "compliance-rules.yaml").read_text())
        cr["sebi_disclosure"]["required"] = True
        (self.conf / "compliance-rules.yaml").write_text(yaml.safe_dump(cr, allow_unicode=True))
        self.slot = cr["sebi_disclosure"]["slot_text"]

    def with_slot(self, text=None, kind="disclosure", fact_ids=None):
        self.to_step4()
        self.write_script(list(BEATS))
        sc = json.loads((self.rd / "04_script" / "script.json").read_text())
        sc["beats"].insert(0, {"id": "B00", "kind": kind, "text": text if text is not None else self.slot, "fact_ids": fact_ids or []})
        (self.rd / "04_script" / "script.json").write_text(json.dumps(sc))
        return self.script_findings()

    def test_script_without_slot_is_blocked(self):
        self.to_step4()
        self.write_script(list(BEATS))
        self.assertIn("disclosure_missing", codes(self.script_findings()))

    def test_placeholder_slot_passes_and_hook_still_required(self):
        f = self.with_slot()
        self.assertNotIn("disclosure_missing", codes(f))
        self.assertNotIn("disclosure_altered", codes(f))
        self.assertNotIn("no_hook", codes(f))

    def test_real_registration_number_is_blocked(self):
        f = self.with_slot(text="Acme Fund House (INZ000000000) | Sam Distributor (ARN-12345)")
        self.assertIn("disclosure_altered", codes(f))

    def test_slot_must_not_cite_facts(self):
        f = self.with_slot(fact_ids=["F001"])
        self.assertIn("disclosure_with_facts", codes(f))

    def test_slot_does_not_count_toward_length_or_review(self):
        f = self.with_slot()
        self.assertNotIn("beat_count", codes(f))
        self.review()
        self.assertNotIn("beat_unreviewed", codes(V.check_semantic_review(run_dir=self.rd)))


if __name__ == "__main__":
    unittest.main()
