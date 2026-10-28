"""Independent real media QA refuses misleading release of partial word highlights."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from selenium_pipeline.original_thomas84_independent_real_media_audit import (
    inspect_real_thomas84_review,
)
from selenium_pipeline.production_video_contract import VideoContractError


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


class IndependentReviewAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parts = []
        candidates = {4: ["s004." + str(k) for k in range(1,6)],
                      5:["s005.text.002"], 6:["s006.text.005"],
                      15:["s015.text.002"], 17:["s017.text.004"]}
        for partnum,(first,last) in enumerate(((1,8),(9,17)),1):
            media = self.root/f"part_{partnum:02d}.mp4"
            movie = f"genuine synthetic unit test movie {partnum}".encode()
            media.write_bytes(movie)
            rows = []
            for slide in range(first,last+1):
                targets = candidates.get(slide,[])
                for i,target in enumerate(targets or [None]):
                    # For each real-candidate historic slide leave a static segment.
                    for tag in ([target,None] if slide!=4 and target else [target]):
                        ident = len(rows)+1
                        clip = self.root/f"part{partnum}_clip_{ident:02d}.mp4"
                        frame = self.root/f"part{partnum}_frame_{ident:02d}.png"
                        clip.write_bytes(f"clip {partnum} {ident}".encode())
                        frame.write_bytes(f"pixel {partnum} {ident}".encode())
                        rows.append(dict(source_slide=slide,candidate_target_id=tag,
                            clip_file=str(clip), image_file=str(frame),
                            candidate_visual_frame_sha256=sha(frame.read_bytes()),
                            actual_encoded_mp4_sha256=sha(clip.read_bytes()),
                            semantic_sync_approved=False))
            self.parts.append(dict(
                part_id=f"part_{partnum:02d}",original_slide_span=[first,last],
                actual_h264_aac_mp4=str(media),actual_MP4_sha256=sha(movie),
                actual_MP4_bytes=len(movie),
                actual_encoded_MP4_duration_s=(419.74 if partnum==1 else 310.84),
                strictly_less_than_ten_minutes=True,
                all_source_visual_audio_units=rows,
                complete_element_synchronization_approved=False,
                student_publication_authorized=False))
        self.receipt = self.root/"receipt.json"
        self.data=dict(schema_version=1,
            status="TWO_REAL_ORIGINAL_8_4_VIDEOS_FOUR_MORE_ACOUSTIC_PDF_HIGHLIGHTS_REVIEW_ONLY",
            real_parts=self.parts,
            protected_original_hashes={"source.pdf":sha(b"original")},
            original_source_sha256=sha(b"original"),
            four_measured_asr_word_timed_original_PDF_highlights=4,
            five_corrected_slide4_actual_PCM_source_highlights=5,
            four_lossless_original_PCM_sample_split_proofs=[
                {"slide":i,"all_samples_recombined_losslessly":True}
                for i in (5,6,15,17)],
            student_accepted_complete_video_parts=0,
            original_PDFs_WAVs_and_MP4s_unchanged=True,
            all_remaining_original_source_elements_speech_synced=False,
            academic_source_mathematics_two_pass_approved=False,
            student_publication_authorized=False,
            whisper_used=False)
        self.save()

    def save(self):
        self.receipt.write_text(json.dumps(self.data),encoding="utf8")

    def inspect(self, probe=None, original=None):
        return inspect_real_thomas84_review(
            receipt=self.receipt, original=original,
            probe=probe or (lambda path: 419.74 if "part_01" in path.name else 310.84))

    def test_true_real_media_hashes_allow_audit_but_never_release(self):
        report=self.inspect()
        self.assertEqual(report["status"],"REAL_MEDIA_REVERIFIED_RELEASE_BLOCKED")
        self.assertEqual(report["distinct_pdf_highlight_candidates"],9)
        self.assertEqual(report["original_slides_covered"],17)
        self.assertEqual(report["historic_slides_still_without_full_semantic_element_sync"],16)
        self.assertFalse(report["student_publication_authorized"])

    def test_altered_clip_rejected(self):
        Path(self.parts[0]["all_source_visual_audio_units"][0]["clip_file"]).write_bytes(b"mutated")
        with self.assertRaisesRegex(VideoContractError,"hash mismatch"):
            self.inspect()

    def test_spurious_release_claims_refused(self):
        self.data["student_publication_authorized"]=True
        self.save()
        with self.assertRaisesRegex(VideoContractError,"falsely approves"):
            self.inspect()

    def test_oversized_actual_encoded_part_rejected(self):
        with self.assertRaisesRegex(VideoContractError,"overlong"):
            self.inspect(probe=lambda path: 600.0)

    def test_missing_original_slide_rejected(self):
        self.parts[1]["all_source_visual_audio_units"]=[
            x for x in self.parts[1]["all_source_visual_audio_units"] if x["source_slide"]!=10]
        self.save()
        with self.assertRaisesRegex(VideoContractError,"all original slides"):
            self.inspect()

    def test_modified_original_source_rejected(self):
        source=self.root/"original"
        source.mkdir()
        (source/"source.pdf").write_bytes(b"modified")
        with self.assertRaisesRegex(VideoContractError,"hash mismatch"):
            self.inspect(original=source)

    def test_external_artifact_path_rejected(self):
        outside=self.root.parent/"out_of_root_not_provided.mp4"
        self.parts[0]["all_source_visual_audio_units"][0]["clip_file"]=str(outside)
        self.save()
        with self.assertRaisesRegex(VideoContractError,"outside saved review"):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
