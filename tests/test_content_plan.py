from pathlib import Path
import tempfile
import unittest

from content_plan import prepare_plan, safe_path, stage_plan


class ContentPlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "guide.md").write_text("A fictional guide", encoding="utf-8")
        self.records = [{
            "id": "DOC-1", "title": "Guide", "source": "guide.md",
            "target": "guidance/guide.md", "category": "Guidance",
            "document_type": "FAQ", "owner": "Content owner", "review_due": "2026-11-16",
        }]

    def tearDown(self):
        self.temporary.cleanup()

    def plan(self):
        return prepare_plan(self.source, self.records, "2026-11-16")

    def test_manifest_records_mapping_hash_and_review_boundary(self):
        plan = self.plan()
        self.assertEqual((plan["total"], plan["ready"], plan["held"]), (1, 1, 0))
        self.assertEqual(len(plan["documents"][0]["sha256"]), 64)
        self.assertEqual(plan["documents"][0]["target"], "guidance/guide.md")

    def test_missing_owner_and_stale_review_hold_content(self):
        self.records[0].update(owner=" ", review_due="2026-11-15")
        plan = self.plan()
        self.assertEqual(plan["held"], 1)
        self.assertEqual(plan["documents"][0]["flags"], ["MISSING_OWNER", "REVIEW_OVERDUE"])

    def test_duplicate_content_holds_both_candidates(self):
        (self.source / "copy.md").write_bytes((self.source / "guide.md").read_bytes())
        other = dict(self.records[0], id="DOC-2", source="copy.md", target="guidance/copy.md")
        self.records.append(other)
        self.assertEqual(self.plan()["held"], 2)

    def test_duplicate_ids_rejected(self):
        self.records.append(dict(self.records[0], target="other.md"))
        with self.assertRaises(ValueError):
            self.plan()

    def test_case_insensitive_target_collision_rejected(self):
        self.records.append(dict(self.records[0], id="DOC-2", target="GUIDANCE/GUIDE.MD"))
        with self.assertRaises(ValueError):
            self.plan()

    def test_invalid_taxonomy_rejected(self):
        self.records[0]["category"] = "Unreviewed category"
        with self.assertRaises(ValueError):
            self.plan()

    def test_missing_source_rejected(self):
        self.records[0]["source"] = "missing.md"
        with self.assertRaises(ValueError):
            self.plan()

    def test_traversal_and_absolute_paths_rejected(self):
        for path in (".", "../outside.md", "/outside.md", "C:/outside.md", "..\\outside.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_path(self.source, path)

    def test_changed_source_rejected_before_publishing(self):
        plan = self.plan()
        (self.source / "guide.md").write_text("Changed after inventory", encoding="utf-8")
        destination = self.root / "stage"
        with self.assertRaises(ValueError):
            stage_plan(self.source, plan, destination)
        self.assertFalse(destination.exists())

    def test_staging_hashes_source_preservation_and_idempotence(self):
        plan = self.plan()
        destination = self.root / "stage"
        before = (self.source / "guide.md").read_bytes()
        self.assertFalse(stage_plan(self.source, plan, destination)["unchanged"])
        self.assertEqual((destination / "guidance/guide.md").read_bytes(), before)
        self.assertEqual((self.source / "guide.md").read_bytes(), before)
        self.assertTrue(stage_plan(self.source, plan, destination)["unchanged"])

    def test_held_content_not_staged(self):
        self.records[0]["owner"] = ""
        destination = self.root / "stage"
        result = stage_plan(self.source, self.plan(), destination)
        self.assertEqual((result["staged"], result["held"]), (0, 1))
        self.assertEqual(list(destination.iterdir()), [])

    def test_existing_unrelated_output_preserved(self):
        destination = self.root / "stage"
        destination.mkdir()
        (destination / "keep.txt").write_text("Keep this", encoding="utf-8")
        with self.assertRaises(ValueError):
            stage_plan(self.source, self.plan(), destination)
        self.assertEqual((destination / "keep.txt").read_text(), "Keep this")

    def test_overlapping_directories_rejected(self):
        with self.assertRaises(ValueError):
            stage_plan(self.source, self.plan(), self.source / "stage")

    def test_invalid_review_date_rejected(self):
        self.records[0]["review_due"] = "not a date"
        with self.assertRaises(ValueError):
            self.plan()


if __name__ == "__main__":
    unittest.main()
