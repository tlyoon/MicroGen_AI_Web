"""One-Send source-only uncaptioned graphic recovery, exercising real worker.

No Gemini, original-source mutation, Figure label fabrication or release QA.
"""
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from selenium_pipeline.figure_uncaptioned_source_recovery import (
    recover_source_uncaptioned_crop, UncaptionedSourceNotProven)


class UncaptionedSourceRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import fitz
        except ImportError:
            raise unittest.SkipTest("PyMuPDF is required for original PDF words")

    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.source=self.root/"source.pdf"
        self.page=self.root/"page_6.png"
        self.page.write_bytes(b"page 6 screenshot - synthetic")
        self.crops=self.root/"crops"
        self.crops.mkdir()
        self.crop=self.crops/"fig_1.png"
        self.crop.write_bytes(b"original source crop for visual symbol, no label")
        self.manifest=self.crops/"page_6_crop_geometry.json"
        self.extra_caption=None
        self.crop_words=["F", "r"]
        self.text_density=22
        self.make_pdf()
        self.make_manifest()

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def make_pdf(self):
        import fitz
        doc=fitz.open()
        for i in range(6):
            page=doc.new_page(width=612,height=783)
            if i==5:
                page.insert_text((72,75),"Summary",fontsize=12)
                for j in range(self.text_density):
                    page.insert_text((76,98+13*j),
                        "Original selectable text describes an object moving through a medium.",
                        fontsize=9)
                for k,label in enumerate(self.crop_words):
                    page.insert_text((510,506+19*k),label,fontsize=11)
                if self.extra_caption is not None:
                    page.insert_text((74,440),self.extra_caption,fontsize=9)
        doc.save(self.source)
        doc.close()

    def make_manifest(self):
        item={
            "schema_version":1,
            "status":"DOCLING_SINGLE_SOURCE_RECT_CANDIDATE",
            "source_pdf_sha256":self.sha(self.source),
            "page_image_sha256":self.sha(self.page),
            "source_page":6,
            "crop_file":"fig_1.png",
            "crop_sha256":self.sha(self.crop),
            "bbox_source_pdf_top_left_pt":[480.0,480.0,570.0,560.0],
            "source_page_size_pt":[612.0,783.0],
            "source_crop_pixel_correspondence_verified":False,
            "original_caption_and_panel_semantics_verified":False,
            "automatic_composite_or_publication_authorized":False,
        }
        self.manifest.write_text(json.dumps({
            "schema_version":1,
            "status":"SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED",
            "original_source_pdf_sha256":self.sha(self.source),
            "page_image_sha256":self.sha(self.page),
            "page_number":6,
            "crop_count":1,
            "crops":[item],
            "source_crop_pixel_correspondence_verified":False,
            "figure_composite_layout_certified":False,
            "student_publication_authorized":False,
        }),encoding="utf-8")

    def recover(self, response="MAPPING_REVIEW_REQUIRED"):
        return recover_source_uncaptioned_crop(
            response=response,source_pdf=self.source,page_png=self.page,
            crops_dir=self.crops,geometry_manifest=self.manifest)

    def test_synthetic_uncaptioned_one_crop_source_identity_only(self):
        original=(self.source.read_bytes(),self.crop.read_bytes(),self.page.read_bytes())
        rows,proof=self.recover()
        self.assertEqual(rows,[(
            "fig_1.png","Unlabeled source graphic",
            "Unlabeled source graphic page_6 fig_1.png")])
        self.assertEqual(proof["status"],
            "UNCAPTIONED_SOURCE_CROP_VERIFIED_NOT_SEMANTIC_QA")
        self.assertFalse(proof["numbered_figure_caption_observed_on_page"])
        self.assertFalse(proof["independent_scientific_and_diagram_semantics_verified"])
        self.assertFalse(proof["source_crop_pixel_correspondence_verified"])
        self.assertFalse(proof["student_publication_authorized"])
        self.assertEqual(proof["new_model_sends"],0)
        self.assertEqual(original,(
            self.source.read_bytes(),self.crop.read_bytes(),self.page.read_bytes()))

    def test_numbered_figure_on_original_page_blocks_generic_guess(self):
        for caption in ("Figure 6.15 Unrelated scientific diagram",
                        "See Figure 6.15 in the text",
                        "Fig. 6.15 A visual proof"):
            with self.subTest(caption=caption):
                self.extra_caption=caption
                self.make_pdf();self.make_manifest()
                with self.assertRaises(UncaptionedSourceNotProven):
                    self.recover()

    def test_ambiguous_or_other_model_reply_never_auto_resolved(self):
        for reply in ("", "MAPPING_REVIEW_REQUIRED\nother", "I can't tell",
                      'fig_1.png : "Figure 6.15" : Figure 6.15.png',
                      "MODEL_FAILED", "MAPPING_REVIEW_REQUIRED AGAIN"):
            with self.subTest(reply=reply):
                with self.assertRaises(UncaptionedSourceNotProven):
                    self.recover(reply)

    def test_undecodable_sparse_pdf_or_text_heavy_crop_not_guessed(self):
        self.text_density=4
        self.make_pdf();self.make_manifest()
        with self.assertRaises(UncaptionedSourceNotProven):
            self.recover()
        self.text_density=22
        self.crop_words=["Mathematics presents actual prose text here"]*7
        self.make_pdf();self.make_manifest()
        with self.assertRaises(UncaptionedSourceNotProven):
            self.recover()

    def test_unsafe_changed_source_or_crop_and_manifest(self):
        self.crop.write_bytes(b"modified after source manifest")
        with self.assertRaises(UncaptionedSourceNotProven):
            self.recover()
        self.make_manifest()
        self.source.write_bytes(self.source.read_bytes()+b"changed")
        with self.assertRaises(UncaptionedSourceNotProven):
            self.recover()

    def test_multiple_crops_and_ambiguous_geometry_fail_closed(self):
        (self.crops/"fig_2.png").write_bytes(b"second unknown crop")
        with self.assertRaises(UncaptionedSourceNotProven):
            self.recover()
        (self.crops/"fig_2.png").unlink()
        record=json.loads(self.manifest.read_text())
        record["crops"][0]["bbox_source_pdf_top_left_pt"]=[480,480,480,560]
        self.manifest.write_text(json.dumps(record))
        with self.assertRaises(UncaptionedSourceNotProven):
            self.recover()

    def test_normal_vendor_worker_one_historical_response_no_resend(self):
        from tests.test_figure_mapping_surplus_reconciliation import (
            ActualNormalFigureWorkerReconciliation)
        calls=[]
        worker,client=ActualNormalFigureWorkerReconciliation.worker(
            self,"MAPPING_REVIEW_REQUIRED",calls)
        original=self.source.read_bytes()
        mapping,produced=worker(client,self.page,self.crops,
                                wait_cap=60,backend_override="selenium",
                                single_attempt=True)
        self.assertEqual(calls,["one_old_response"])
        self.assertEqual([p.name for p in produced],
            ["Unlabeled source graphic page_6 fig_1.png"])
        self.assertEqual((self.crops/produced[0].name).read_bytes(),self.crop.read_bytes())
        self.assertIn("Unlabeled source graphic",
                      mapping.read_text(encoding="utf8"))
        raw=self.page.with_name("page_6_uncaptioned_model_reply.raw.txt")
        proof=self.page.with_name("page_6_uncaptioned_source_evidence.json")
        self.assertEqual(raw.read_text(encoding="utf8"),"MAPPING_REVIEW_REQUIRED\n")
        witness=json.loads(proof.read_text(encoding="utf8"))
        self.assertEqual(witness["saved_model_reply_sha256"],self.sha(raw))
        self.assertEqual(witness["source_pdf_sha256"],self.sha(self.source))
        self.assertFalse(witness["student_publication_authorized"])
        self.assertEqual(original,self.source.read_bytes())

    def test_actual_watcher_recognizes_completed_owned_refusal_quickly(self):
        """No 90-s wait when the *owned* response is a stable refusal."""
        import ast
        import os
        import time
        from types import SimpleNamespace
        vendor=(Path(__file__).resolve().parents[1]/
                "selenium_pipeline"/"vendor_template_v2"/
                "map_and_rename_selenium_v8.py")
        tree=ast.parse(vendor.read_text(encoding="utf8"))
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
               and n.name=="wait_for_mapping_response_ready")
        marker="MAPPING_REVIEW_REQUIRED"
        class ModelElement:
            def is_displayed(self):
                return True
        class StopElement:
            def is_displayed(self):
                return True
            def is_enabled(self):
                return True
        class Driver:
            current_window_handle="microgen_owned"
            current_url="https://gemini.google.com/app"
            has_model=True
            generating=False
            def find_elements(self,by,selector):
                if by=="css selector" and selector=="model-response":
                    return [ModelElement()] if self.has_model else []
                if by=="xpath" and self.generating:
                    return [StopElement()]
                return []
            def execute_script(self,script):
                return {"text":marker,"generating":self.generating}
        ns={
            "os":os,"time":time,"log":lambda *args:None,
            "clean_model_text":lambda t:t,
            "get_latest_response_text":lambda driver:marker,
            "parse_mapping_lines":lambda text:[],
            "GeminiGenerationStalled":RuntimeError,
        }
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=[f],type_ignores=[])),str(vendor),"exec"),ns)
        driver=Driver()
        client=SimpleNamespace(driver=driver,_automation_tab="microgen_owned")
        start=time.monotonic()
        self.assertEqual(ns[f.name](client,timeout=2,poll=0.05),marker)
        self.assertLess(time.monotonic()-start,1.5)
        for flags in (
            {"has_model":False,"generating":False},
            {"has_model":True,"generating":True}):
            with self.subTest(flags=flags):
                driver.has_model=flags["has_model"]
                driver.generating=flags["generating"]
                self.assertEqual(ns[f.name](client,timeout=.18,poll=.05),"")
        driver.has_model=True
        driver.generating=False
        self.assertEqual(ns[f.name](
            client,baseline_text=marker,timeout=.18,poll=.05),"")

    def test_normal_worker_then_actual_sha_bound_page_checkpoint(self):
        """A generic uncaptioned crop can be structurally checkpointed, not QA."""
        import shutil
        from tests.test_figure_mapping_surplus_reconciliation import (
            ActualNormalFigureWorkerReconciliation)
        from selenium_pipeline.figure_mapping_checkpoints import (
            save_checkpoint, checkpoint_can_resume)
        page_dir=self.root/"pages"/"page_6"
        page_dir.mkdir(parents=True)
        new_page=page_dir/"page_6.png"
        self.page.rename(new_page)
        new_crop_dir=self.crops/"page_6"
        new_crop_dir.mkdir()
        new_crop=new_crop_dir/"fig_1.png"
        self.crop.rename(new_crop)
        self.manifest.unlink()
        self.page=new_page
        self.crops=new_crop_dir
        self.crop=new_crop
        self.manifest=self.crops/"page_6_crop_geometry.json"
        self.make_manifest()
        shutil.copyfile(self.manifest,page_dir/self.manifest.name)
        calls=[]
        worker,client=ActualNormalFigureWorkerReconciliation.worker(
            self,"MAPPING_REVIEW_REQUIRED",calls)
        mapping, produced=worker(
            client,self.page,self.crops,wait_cap=60,
            backend_override="selenium",single_attempt=True)
        self.assertEqual(calls,["one_old_response"])
        self.assertEqual(len(produced),1)
        shutil.copy2(produced[0],self.root/produced[0].name)
        transport=self.crops/"gemini_transport_attempts.json"
        transport.write_text(json.dumps({
            "page":6,"completed":True,
            "attempts":[{"backend":"selenium","attempt":1,
                         "status":"validated"}]}),encoding="utf-8")
        receipt=save_checkpoint(self.root,6,copy_to_root=True)
        self.assertTrue(receipt.is_file())
        self.assertTrue(checkpoint_can_resume(self.root,6,copy_to_root=True))
        receipt_data=json.loads(receipt.read_text())
        self.assertEqual(receipt_data["mapped"][0]["caption"],
                         "Unlabeled source graphic")
        self.assertEqual(receipt_data["status"],
                         "validated_source_mapping_not_visual_approval")
        self.assertEqual(self.sha(produced[0]),self.sha(self.crop))
        from selenium_pipeline.runner import valid
        self.assertTrue(valid("figures",self.root))
        # Tampering with the provenance after the real worker checkpoint
        # must revoke both reusability and even structural figure readiness.
        evidence=self.page.with_name(
            "page_6_uncaptioned_source_evidence.json")
        evidence.write_bytes(evidence.read_bytes()+b"changed")
        self.assertFalse(checkpoint_can_resume(
            self.root,6,copy_to_root=True))
        self.assertFalse(valid("figures",self.root))

    def test_normal_vendor_worker_rejects_uncertain_source_without_output(self):
        from tests.test_figure_mapping_surplus_reconciliation import (
            ActualNormalFigureWorkerReconciliation)
        self.extra_caption="Figure 6.15 The legitimate printed caption"
        self.make_pdf();self.make_manifest()
        calls=[]
        worker,client=ActualNormalFigureWorkerReconciliation.worker(
            self,"MAPPING_REVIEW_REQUIRED",calls)
        with self.assertRaises(RuntimeError):
            worker(client,self.page,self.crops,wait_cap=60,
                   backend_override="selenium",single_attempt=True)
        self.assertEqual(calls,["one_old_response"])
        self.assertEqual(set(p.name for p in self.crops.glob("*.png")),
                         {"fig_1.png"})
        self.assertFalse(self.page.with_name(
            "page_6_uncaptioned_source_evidence.json").exists())

if __name__=="__main__":
    unittest.main()
