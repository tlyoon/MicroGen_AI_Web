"""Adversarial original-PDF panel marker reconciliation, no model Send."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from selenium_pipeline.figure_source_panel_caption import (
    SourcePanelEvidenceError, reconcile_parent_caption_panels)


class PanelPdfTests(unittest.TestCase):
    def setUp(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root/"source.pdf"
        self.page_image = root/"page_1.png"
        self.page_image.write_bytes(b"synthetic page PNG identity only")
        self.crops = root/"crops"
        self.crops.mkdir()
        self.figures = ("fig_1.png","fig_2.png")
        for i,name in enumerate(self.figures):
            (self.crops/name).write_bytes(b"unique synthetic source crop "+str(i).encode())
        self.manifest = self.crops/"page_1_crop_geometry.json"
        self.rects = [[100.0,100.0,200.0,200.0],
                      [100.0,250.0,200.0,350.0]]
        self.words = [("a",108,193),("b",108,343)]
        self.caption = "Figure 3.4 (a) First panel (b) Second panel"
        self.make_pdf()
        self.make_manifest()
        self.mappings=[
            ("fig_1.png","Figure 3.4","Figure 3.4(a).png"),
            ("fig_2.png","Figure 3.4","Figure 3.4(b).png"),
        ]

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def make_pdf(self):
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=612,height=783)
        for letter,x,y in self.words:
            page.insert_text((x,y),letter,fontsize=11)
        if self.caption is not None:
            page.insert_text((103,380),self.caption,fontsize=9)
        doc.save(self.source)
        doc.close()

    def make_manifest(self):
        records=[]
        for i,name in enumerate(self.figures):
            records.append({
                "schema_version":1,
                "status":"DOCLING_SINGLE_SOURCE_RECT_CANDIDATE",
                "source_pdf_sha256":self.sha(self.source),
                "page_image_sha256":self.sha(self.page_image),
                "source_page":1,
                "crop_file":name,"crop_sha256":self.sha(self.crops/name),
                "bbox_source_pdf_top_left_pt":self.rects[i],
                "source_page_size_pt":[612.0,783.0],
                "source_crop_pixel_correspondence_verified":False,
                "original_caption_and_panel_semantics_verified":False,
                "automatic_composite_or_publication_authorized":False,
            })
        self.manifest.write_text(json.dumps({
            "schema_version":1,
            "status":"SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED",
            "original_source_pdf_sha256":self.sha(self.source),
            "page_image_sha256":self.sha(self.page_image),
            "page_number":1, "crop_count":len(records),
            "crops":records,
            "source_crop_pixel_correspondence_verified":False,
            "figure_composite_layout_certified":False,
            "student_publication_authorized":False,
        }),encoding="utf-8")

    def reconcile(self, mappings=None):
        return reconcile_parent_caption_panels(
            mappings=self.mappings if mappings is None else mappings,
            source_pdf=self.source,
            page_png=self.page_image,
            crops_dir=self.crops,
            geometry_manifest=self.manifest)

    def test_true_independent_caption_and_corner_letters(self):
        before=[p.read_bytes() for p in
                (self.source,self.page_image,self.manifest)]
        resolved, witness=self.reconcile()
        self.assertEqual([x[1] for x in resolved],
                         ["Figure 3.4(a)","Figure 3.4(b)"])
        self.assertEqual(witness["status"],
                         "SOURCE_TEXT_AND_CROP_PANEL_MARKERS_CORROBORATED_NOT_FIGURE_QA")
        self.assertEqual([r["panel_letter"] for r in witness["source_panel_proof"]],
                         ["a","b"])
        self.assertFalse(witness["student_publication_authorized"])
        self.assertFalse(witness["full_source_crop_pixel_correspondence_verified"])
        self.assertEqual([p.read_bytes() for p in
                (self.source,self.page_image,self.manifest)],before)

    def test_non_panel_model_mapping_unchanged(self):
        original=[("fig_1.png","Figure 3.4","Figure 3.4.png")]
        self.assertEqual(self.reconcile(original),(original,None))

    def test_missing_source_caption_or_panel_description(self):
        for caption in (None,"Figure 3.4 A first and B second",
                        "Figure 3.4 (a) only", "Figure 3.5 (a) and (b)"):
            with self.subTest(caption=caption):
                self.caption=caption
                self.make_pdf();self.make_manifest()
                with self.assertRaises(SourcePanelEvidenceError):
                    self.reconcile()

    def test_duplicate_or_missing_corner_source_markers(self):
        for words in (
                [("a",108,193)],
                [("a",108,193),("a",119,193),("b",108,343)],
                [("a",108,193),("c",108,343)],
                [("a",188,193),("b",108,343)],
                [("a",108,130),("b",108,343)],
        ):
            with self.subTest(words=words):
                self.words=words
                self.make_pdf();self.make_manifest()
                with self.assertRaises(SourcePanelEvidenceError):
                    self.reconcile()

    def test_crop_and_pdf_bytes_must_match_bound_provenance(self):
        (self.crops/"fig_2.png").write_bytes(b"changed but still same name")
        with self.assertRaises(SourcePanelEvidenceError):
            self.reconcile()
        self.make_manifest()
        self.source.write_bytes(self.source.read_bytes()+b"mutation")
        with self.assertRaises(SourcePanelEvidenceError):
            self.reconcile()

    def test_wrong_panel_target_duplication_and_reordering_fail(self):
        variants=[
            [self.mappings[0],("fig_2.png","Figure 3.4","Figure 3.4(a).png")],
            [("fig_1.png","Figure 3.4","Figure 3.4(b).png"),
             ("fig_2.png","Figure 3.4","Figure 3.4(a).png")],
            [self.mappings[0],("fig_2.png","Figure 3.5","Figure 3.5(b).png")],
            [("fig_1.png","Figure 3.4","Figure 3.4.png"),self.mappings[1]],
        ]
        for m in variants:
            with self.subTest(m=m):
                with self.assertRaises(SourcePanelEvidenceError):
                    self.reconcile(m)

    def test_unverifiable_geometry_or_citation_fails_closed(self):
        self.rects[1]=[100.0,100.0,200.0,200.0]
        self.make_manifest()
        with self.assertRaises(SourcePanelEvidenceError):
            self.reconcile()

    def test_actual_vendor_mapping_worker_source_only_corrob_and_one_old_response(self):
        """Execute the NORMAL vendor worker with fake response, zero live Sends."""
        from tests.test_figure_mapping_surplus_reconciliation import (
            ActualNormalFigureWorkerReconciliation)
        self.root = self.source.parent
        self.page = self.page_image
        raw = ('fig_1.png : "Figure 3.4" : Figure 3.4(a).png\n'
               'fig_2.png : "Figure 3.4" : Figure 3.4(b).png')
        calls = []
        worker, client = ActualNormalFigureWorkerReconciliation.worker(
            self,raw,calls)
        source_before = self.source.read_bytes()
        mapping, produced = worker(
            client, self.page_image, self.crops,wait_cap=60,
            backend_override="selenium",single_attempt=True)
        self.assertEqual(calls,["one_old_response"])
        self.assertEqual([p.name for p in produced],
                         ["Figure 3.4(a).png","Figure 3.4(b).png"])
        self.assertTrue(mapping.is_file())
        self.assertIn("Figure 3.4(a)",mapping.read_text())
        witness_path=self.page_image.with_name(
            "page_1_source_panel_caption_evidence.json")
        self.assertTrue(witness_path.is_file())
        witness=json.loads(witness_path.read_text(encoding="utf-8"))
        self.assertEqual(witness["source_pdf_sha256"],self.sha(self.source))
        self.assertEqual(witness["source_panel_proof"][0]["panel_letter"],"a")
        self.assertEqual(witness["source_panel_proof"][1]["panel_letter"],"b")
        self.assertFalse(witness["student_publication_authorized"])
        self.assertEqual(self.source.read_bytes(),source_before)

    def test_actual_vendor_worker_unverified_marker_refuses_to_publish(self):
        from tests.test_figure_mapping_surplus_reconciliation import (
            ActualNormalFigureWorkerReconciliation)
        self.root=self.source.parent
        self.page=self.page_image
        # Original PDF lacks the (b) letter. Do NOT use model target alone.
        self.words=[("a",108,193)]
        self.make_pdf()
        self.make_manifest()
        raw = ('fig_1.png : "Figure 3.4" : Figure 3.4(a).png\n'
               'fig_2.png : "Figure 3.4" : Figure 3.4(b).png')
        calls=[]
        worker,client=ActualNormalFigureWorkerReconciliation.worker(self,raw,calls)
        from selenium_pipeline.figure_composites import FigureCompositeReviewRequired
        with self.assertRaises(FigureCompositeReviewRequired):
            worker(client,self.page_image,self.crops,wait_cap=60,
                   backend_override="selenium",single_attempt=True)
        self.assertEqual(calls,["one_old_response"])
        self.assertFalse((self.crops/"Figure 3.4(a).png").exists())
        self.assertFalse((self.crops/"Figure 3.4(b).png").exists())
        self.assertFalse(self.page_image.with_name(
            "page_1_source_panel_caption_evidence.json").exists())

    def test_vendor_normal_path_calls_before_composite_validation(self):
        from selenium_pipeline import figure_source_panel_caption
        source=(Path(figure_source_panel_caption.__file__).parent/
                "vendor_template_v2"/"map_and_rename_selenium_v8.py").read_text(
                    encoding="utf-8")
        self.assertIn("reconcile_parent_caption_panels(", source)
        self.assertIn("Source-only SHA-bound panel-caption", source)
        self.assertIn("_source_panel_caption_evidence.json", source)
        self.assertLess(source.index("resolved_triples, panel_source_witness = reconcile_parent_caption_panels"),
                        source.index("resolved_triples = validate_and_prepare_mappings"))


if __name__=="__main__":
    unittest.main()
