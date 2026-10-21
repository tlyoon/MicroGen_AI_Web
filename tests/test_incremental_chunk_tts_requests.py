import tempfile,unittest,hashlib
from pathlib import Path
from selenium_pipeline.incremental_chunk_tts_requests import prepare_chunk_jobs,save_unpaid_job_manifest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha

def generate(tmp):
    root=Path(tmp)/"source";root.mkdir()
    for name in ("source.pdf","slides.pdf","script.txt"):
        (root/name).write_bytes(name.encode())
    hashes=[_sha(root/n) for n in ("source.pdf","slides.pdf","script.txt")]
    line="Verify this named integral expression aloud."
    u={"utterance_id":"s001.utterance.001",
       "slide":1,"spoken_text":line,
       "spoken_text_sha256":hashlib.sha256(line.encode()).hexdigest(),
       "target_id":"s001.text.001","bbox_pdf_pt":[10,20,70,40],
       "original_source_page":1,"reviewer_attestation_present":True,
       "independently_proven_spoken_audio_fidelity":False}
    record={"status":"EXPLICIT_NONLITERAL_ELEMENT_SELECTIONS_SOURCE_BOUND",
            "source_sha256":hashes[0],"slides_sha256":hashes[1],
            "script_sha256":hashes[2],"selected_segments":[u],
            "unreviewed_utterance_count":2,
            "tts_billing_authorized":False,"student_publication_authorized":False}
    return root,record

class UnpaidExactTTSJobs(unittest.TestCase):
    def test_script_hash_voice_model_and_external_staging(self):
        with tempfile.TemporaryDirectory() as t:
            folder,review=generate(t)
            result=prepare_chunk_jobs(source=folder/"source.pdf",
                  slides=folder/"slides.pdf",script=folder/"script.txt",reviewed=review)
            self.assertEqual(result["job_count"],1)
            self.assertEqual(result["voice"],"Kore")
            self.assertEqual(result["model"],"gemini-3.8-flash-lite-tts")
            self.assertFalse(result["paid_tts_execution_authorized"])
            self.assertEqual(result["chunk_jobs"][0]["job_id"],"s001.utterance.001")
            path=Path(t)/"reviewed_jobs.json"
            save_unpaid_job_manifest(result,output=path,original_folder=folder)
            self.assertTrue(path.exists())
            with self.assertRaises(FileExistsError):
                save_unpaid_job_manifest(result,output=path,original_folder=folder)
    def test_stale_source_or_mutated_spoken_chunk_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder,review=generate(t)
            review["selected_segments"][0]["spoken_text"]+=" mutated"
            with self.assertRaises(FigureIdentityReviewRequired):
                prepare_chunk_jobs(source=folder/"source.pdf",
                   slides=folder/"slides.pdf",script=folder/"script.txt",reviewed=review)
            review["selected_segments"][0]["spoken_text"]="Verify this named integral expression aloud."
            (folder/"slides.pdf").write_bytes(b"changed")
            with self.assertRaises(FigureIdentityReviewRequired):
                prepare_chunk_jobs(source=folder/"source.pdf",
                   slides=folder/"slides.pdf",script=folder/"script.txt",reviewed=review)
