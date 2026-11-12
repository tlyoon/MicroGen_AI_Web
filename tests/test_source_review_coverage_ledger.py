"""Original-job coverage receipts: missing and untrusted never count as reviewed."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.source_review_coverage_ledger import (
    aggregate,SourceCoverageBlocked)
from selenium_pipeline.evidence_reuse_contract import file_sha256

class SourceCoverageIntegrityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.src=self.root/"source"
        self.src.mkdir()
        self.jobs=self.root/"jobs"
        self.jobs.mkdir()
        self.h={}
        for name in ["source.pdf","slides.pdf","script.txt"]:
            p=self.src/name
            p.write_bytes(("TEST ONLY "+name).encode())
            self.h[name[:-4] if name.endswith(".pdf") else "script"]=file_sha256(p)
        self.entries=[]
        self.docs=[]
        for i,count in ((1,1),(2,2)):
            units=[{"id":f"s{i:03d}.utterance.{k:03d}",
                    "spoken_sha256":hashlib.sha256(
                        f"{i}-{k}".encode()).hexdigest()}
                   for k in range(1,count+1)]
            doc={
                "source_sha256":self.h["source"],
                "slides_sha256":self.h["slides"],
                "script_sha256":self.h["script"],
                "selected_original_slides":[i],
                "slides":[{"slide":i,"utterances":units}],
                "verified_source_quote_candidates_v1":{
                    "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
                    "utterances":[{"utterance_id":u["id"]}
                                  for u in units]}
            }
            name=f"job_{i:02d}.json"
            (self.jobs/name).write_text(json.dumps(doc),encoding="utf8")
            self.entries.append({"job_filename":name,
                                 "job_sha256":file_sha256(self.jobs/name),
                                 "slides":[i],"utterance_count":count})
            self.docs.append(doc)
        manifest={
            "source_folder":str(self.src),
            "source_sha256":self.h["source"],
            "slides_sha256":self.h["slides"],
            "script_sha256":self.h["script"],
            "total_slides":2,
            "jobs":self.entries}
        self.manifest=self.jobs/"source_citation_batch_manifest.json"
        self.manifest.write_text(json.dumps(manifest),encoding="utf8")
        self.dest=self.root/"coverage.json"
        self.rows=[{
            "utterance_id":u["id"],
            "spoken_sha256":u["spoken_sha256"],
            "verdict":"UNRESOLVED",
            "target_id":None,
            "source_page":None,
            "verbatim_source_quote":None,
            "math_explanation":"A sufficiently detailed scientific statement is unresolved."
        } for d in self.docs for slide in d["slides"]
           for u in slide["utterances"]]
        self.full=self.root/"full.json"
        self.full.write_text(json.dumps({
            "status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
            "rows":[self.rows[0]],"review_count":1,
            "student_publication_authorized":False,
            "academic_mathematics_independently_verified":False}),
            encoding="utf8")
        self.checkpoint=self.root/"previous_checkpoint"
        self.checkpoint.mkdir()
        self.raw={"rows":self.rows[1:]}
        raw=self.checkpoint/"model_response_untrusted.txt"
        raw.write_text(json.dumps(self.raw),encoding="utf8")
        self.partial=self.root/"partial.json"
        self.partial.write_text(json.dumps({
            "status":"PARTIAL_SOURCE_WITNESSED_AI_REVIEW_NOT_COMPLETE",
            "source_batch_job_sha256":self.entries[1]["job_sha256"],
            "source_sha256":self.h["source"],
            "slides_sha256":self.h["slides"],
            "script_sha256":self.h["script"],
            "new_model_or_tts_requests":0,
            "original_submission_preserved_no_resend":True,
            "full_source_and_math_review_accepted":False,
            "source_model_response_sha256":file_sha256(raw),
            "original_dispatch_checkpoint":str(self.checkpoint),
            "accepted_rows":[self.rows[1]],
            "untrusted_rows":[{"utterance_id":self.rows[2]["utterance_id"]}]
        }),encoding="utf8")

    def _aggregate(self,results):
        def approved_only_after_source_recheck(*,folder,job,slide,unit,row):
            self.assertEqual(folder,self.src)
            self.assertEqual(unit["id"],row["utterance_id"])
            return dict(row)
        with patch("selenium_pipeline.source_review_coverage_ledger._validated_row",
                   side_effect=approved_only_after_source_recheck):
            return aggregate(manifest_path=self.manifest,
                             results=results,out=self.dest)

    def test_reconciles_full_partial_untrusted_without_claiming_approval(self):
        answer=self._aggregate([self.full,self.partial])
        self.assertEqual(answer["original_utterance_count"],3)
        self.assertEqual(answer["individually_source_validated"],2)
        self.assertEqual(answer["untrusted_utterances"],1)
        self.assertEqual(answer["not_yet_reviewed_utterances"],0)
        self.assertFalse(answer["release_approved"])
        self.assertEqual(answer["new_model_tts_requests"],0)

    def test_duplicate_job_or_changed_quotation_evidence_rejected(self):
        with self.assertRaises(SourceCoverageBlocked):
            self._aggregate([self.full,self.full])
        self.assertFalse(self.dest.exists())
        original=self.checkpoint/"model_response_untrusted.txt"
        original.write_bytes(original.read_bytes()+b"changed")
        with self.assertRaises(SourceCoverageBlocked):
            self._aggregate([self.full,self.partial])
        self.assertFalse(self.dest.exists())

if __name__=="__main__":
    unittest.main()
