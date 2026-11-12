"""Tests for step 5 (design) and step 6 (animation). FIXTURE data only. Rendering is not run here (needs Chrome);
the video checks are tested on manifests built with --no-render.

Run:  python3 -I -m unittest discover -s tests -v
"""
import copy
import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))
from test_engine import BEATS, Base, codes  # noqa: E402
import animate  # noqa: E402
import design  # noqa: E402
import validators as V  # noqa: E402


class StepFiveSix(Base):
    def setUp(self):
        super().setUp()
        cr = yaml.safe_load((self.conf / "compliance-rules.yaml").read_text())
        cr["sebi_disclosure"]["required"] = True
        (self.conf / "compliance-rules.yaml").write_text(yaml.safe_dump(cr, allow_unicode=True))
        self.slot = cr["sebi_disclosure"]["slot_text"]

    def to_step5(self):
        self.to_step4()
        self.write_script(list(BEATS), fmt="carousel")
        sc = json.loads((self.rd / "04_script" / "script.json").read_text())
        sc["beats"].insert(0, {"id": "B00", "kind": "disclosure", "text": self.slot, "fact_ids": [], "key_point": None})
        (self.rd / "04_script" / "script.json").write_text(json.dumps(sc, ensure_ascii=False))
        self.review()
        self.cli("approve", self.run_id, "G4", "--by", "Cara Lead", "--decision", "approve")
        self.cli("advance", self.run_id)

    def build(self):
        sp = self.rd / "04_script" / "script.json"
        return design.build(V.load_json(sp), "carousel", self.rd / "05_design", self.conf, V.sha256_file(sp), previews=False)

    def design_codes(self):
        return codes(V.check_design(run_dir=self.rd, config_dir=self.conf))

    # ---- step 5

    def test_after_g4_run_moves_to_step5(self):
        self.to_step5()
        st = json.loads((self.rd / "state.json").read_text())
        self.assertEqual(st["step"], 5)
        self.assertTrue((self.rd / "handoff.json").exists())

    def test_built_design_passes_and_carries_exact_words(self):
        self.to_step5()
        d = self.build()
        self.assertEqual(self.design_codes(), set())
        content = [b for b in BEATS]
        self.assertEqual(len(d["pages"]), len(content))
        texts = [l["text"] for p in d["pages"] for l in p["layers"] if l["role"] == "script"]
        self.assertEqual(texts, [b[4] for b in content])

    def edit_layer(self, role, fn):
        p = self.rd / "05_design" / "design.json"
        d = json.loads(p.read_text())
        for page in d["pages"]:
            for l in page["layers"]:
                if l["role"] == role:
                    fn(l)
                    p.write_text(json.dumps(d, ensure_ascii=False))
                    return

    def test_changed_word_is_blocked(self):
        self.to_step5(); self.build()
        self.edit_layer("script", lambda l: l.update(text=l["text"].replace("SIP", "SIP plan")))
        self.assertIn("design_text_changed", self.design_codes())

    def test_filled_disclosure_is_blocked(self):
        self.to_step5(); self.build()
        self.edit_layer("disclosure", lambda l: l.update(text="Some Distributor (ARN-1)"))
        self.assertIn("design_disclosure_altered", self.design_codes())

    def test_extra_text_is_blocked(self):
        self.to_step5(); self.build()
        self.edit_layer("rule", lambda l: l.update(kind="text", text="Best fund!", color="#000000", font_size=40, lines=["Best fund!"]))
        self.assertIn("design_extra_text", self.design_codes())

    def test_low_contrast_is_blocked(self):
        self.to_step5(); self.build()
        self.edit_layer("script", lambda l: l.update(color="#EEEAE0"))
        self.assertIn("design_low_contrast", self.design_codes())

    def test_script_edit_after_design_is_stale(self):
        self.to_step5(); self.build()
        sp = self.rd / "04_script" / "script.json"
        sp.write_text(sp.read_text() + " ")
        self.assertIn("design_stale", self.design_codes())

    def test_g5_needs_content_lead_and_image_format_skips_step6(self):
        self.to_step5(); self.build()
        out = self.cli("approve", self.run_id, "G5", "--by", "Rita Researcher", "--decision", "approve", expect=2)
        self.assertIn("not allowed", out)
        self.cli("approve", self.run_id, "G5", "--by", "Cara Lead", "--decision", "approve")
        out = self.cli("advance", self.run_id)
        self.assertIn("skipped", out)
        st = json.loads((self.rd / "state.json").read_text())
        self.assertEqual(st["status"], "ready_for_review")
        self.assertTrue((self.rd / "handoff_media.json").exists())

    def test_design_edit_after_g5_voids_approval(self):
        self.to_step5(); self.build()
        self.cli("approve", self.run_id, "G5", "--by", "Cara Lead", "--decision", "approve")
        self.edit_layer("progress", lambda l: l.update(w=l["w"] + 1))
        out = self.cli("advance", self.run_id, expect=2)
        self.assertIn("changed after G5", out)

    # ---- step 6 (manifest level)

    def video(self):
        self.to_step5(); d = self.build()
        dp = self.rd / "05_design" / "design.json"
        out = self.rd / "06_animation"
        man = animate.run(dp, out, self.conf, do_render=False)
        return man, d, dp

    def test_video_manifest_passes_without_mp4_check(self):
        man, d, dp = self.video()
        self.assertEqual(codes(V.check_video_data(man, d, self.conf, V.sha256_file(dp))), set())
        self.assertEqual(man["scenes"][0]["kind"], "slate")

    def test_video_text_change_and_missing_slate_are_blocked(self):
        man, d, dp = self.video()
        bad = copy.deepcopy(man)
        bad["scenes"][2]["texts"][-1]["text"] += " Guaranteed."
        self.assertIn("video_text_changed", codes(V.check_video_data(bad, d, self.conf)))
        bad = copy.deepcopy(man)
        bad["scenes"].pop(0)
        self.assertIn("video_no_disclosure_slate", codes(V.check_video_data(bad, d, self.conf)))

    def test_video_too_fast_is_blocked(self):
        man, d, dp = self.video()
        bad = copy.deepcopy(man)
        bad["scenes"][1]["frames"] = 15
        self.assertIn("video_too_fast", codes(V.check_video_data(bad, d, self.conf)))

    def test_missing_mp4_is_blocked(self):
        man, d, dp = self.video()
        self.assertIn("video_missing", codes(V.check_video_data(man, d, self.conf, None, self.rd / "06_animation" / "video.mp4")))


if __name__ == "__main__":
    unittest.main()


class StyledDesign(unittest.TestCase):
    """The styled renderer's output is checked with the same rules (no browser needed for this part)."""
    def test_layout_to_design_is_checked(self):
        import styled_design as SD
        conf = ROOT / "config"
        slot = yaml.safe_load((conf / "compliance-rules.yaml").read_text())["sebi_disclosure"]["slot_text"]
        script = {"format": "carousel", "beats": [{"id": "B00", "kind": "disclosure", "text": slot},
                  {"id": "B01", "kind": "hook", "text": "Salary day. What does the data show?"}]}
        content = SD.content_for(script, {"style": "risograph", "pages": [{"beat": "B01", "scene": "morning"}]}, slot)
        lay = [{"id": "P01", "layout": [
            {"role": "script", "text": "Salary day. What does the data show?", "lines": ["Salary day. What does", "the data show?"], "x": 86, "y": 250, "w": 908, "h": 170,
             "font_size": 72, "font_weight": 800, "font_family": "Bricolage Grotesque", "line_height": 1.18, "color": "#3D5588", "align": "left", "beat_id": "B01"},
            {"role": "disclosure", "text": slot, "lines": [slot], "x": 86, "y": 1300, "w": 908, "h": 26, "font_size": 22, "font_weight": 500,
             "font_family": "Bricolage Grotesque", "line_height": 1.18, "color": "#3D5588", "align": "center", "beat_id": "B00"}]}]
        brand = yaml.safe_load((conf / "brand.yaml").read_text())
        d = SD.to_design(content, lay, "risograph", None, brand)
        self.assertEqual(codes(V.check_design_data(d, script, conf)), set())
        lay[0]["layout"][0]["text"] = "Salary day. Guaranteed growth."
        d = SD.to_design(content, lay, "risograph", None, brand)
        self.assertIn("design_text_changed", codes(V.check_design_data(d, script, conf)))
        f = SD.to_fabric(d)
        self.assertEqual(f["pages"][0]["canvas"]["backgroundImage"]["src"], "P01-art.png")


class ReelCards(unittest.TestCase):
    def setUp(self):
        self.conf = ROOT / "config"
        self.slot = yaml.safe_load((self.conf / "compliance-rules.yaml").read_text())["sebi_disclosure"]["slot_text"]
        self.facts = {"F001": {"statement": "Fixture: 32,160 collected in October 2026.", "nums": ["32,160", "October 2026"]}}
        self.reel = {"slot": self.slot, "frames": 450, "cuts": [60, 150, 270, 360],
                     "cards": [{"line": "Salary day."}, {"line": "How many others got one?"},
                               {"big": "₹32,160 crore", "line": "collected in October 2026.", "fact_ids": ["F001"]},
                               {"line": "Save this for later."}, {"line": "Source: AMFI."}]}

    def test_clean_reel_passes(self):
        self.assertEqual(codes(V.check_reel_cards(self.reel, self.facts, self.conf)), set())

    def test_uncited_number_long_reel_and_filled_slot_are_blocked(self):
        r = copy.deepcopy(self.reel)
        r["cards"][3]["line"] = "Up 12% this year."
        r["frames"] = 700
        r["slot"] = "Some Distributor ARN-1"
        c = codes(V.check_reel_cards(r, self.facts, self.conf))
        self.assertTrue({"reel_number_not_in_fact", "reel_too_long", "reel_disclosure_altered"} <= c)


class SilentFilmStyle(unittest.TestCase):
    def test_style_registered_for_short_reels(self):
        st = yaml.safe_load((ROOT / "config" / "styles.yaml").read_text())["styles"]["silent_film"]
        self.assertIn("reels_short", st["formats"])
        self.assertTrue(any("plaque" in r for r in st["rules"]))

    def test_rmwdezgf7_props_under_20s_with_placeholder_slot(self):
        import json
        p = json.loads((ROOT / "tools/remotion/src/silent/silent-rmwdezgf7.json").read_text())
        slot = yaml.safe_load((ROOT / "config" / "compliance-rules.yaml").read_text())["sebi_disclosure"]["slot_text"]
        self.assertLess(p["frames"] / 30, 20)
        self.assertEqual(p["slot"], slot)
        cards = [{"line": " ".join(l["text"] for l in s["lines"]), "fact_ids": s.get("fact_ids", [])}
                 for s in p["shots"] if s["kind"] == "card"]
        self.assertTrue(all(s["to"] > s["from"] for s in p["shots"]))
        self.assertGreaterEqual(len(cards), 4)


class ConsoleBridge(unittest.TestCase):
    def setUp(self):
        import importlib, sys
        sys.path.insert(0, str(ROOT / "tools"))
        self.B = importlib.import_module("console_bridge")
        slot = yaml.safe_load((ROOT / "config" / "compliance-rules.yaml").read_text())["sebi_disclosure"]["slot_text"]
        self.dump = {"meta": {"format": "carousel", "gates": {"G4": {}}, "selected": {"angle": "A1"}},
                     "angles": [{"id": "A1", "core_message": "October 2026 SIP was ₹32,160 crore."}],
                     "beats": [{"id": "B01", "kind": "hook", "text": "A headline says SIP money dipped."},
                               {"id": "B00", "kind": "disclosure", "text": slot}]}

    def test_script_sorted_and_needs_g4(self):
        s = self.B.script_from_dump(self.dump)
        self.assertEqual([b["id"] for b in s["beats"]], ["B00", "B01"])
        self.assertEqual(s["beats"][1]["fact_ids"], [])
        d = copy.deepcopy(self.dump); d["meta"]["gates"] = {}
        with self.assertRaises(SystemExit):
            self.B.script_from_dump(d)
