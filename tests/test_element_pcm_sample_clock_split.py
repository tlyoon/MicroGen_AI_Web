import unittest
from selenium_pipeline.element_pcm_sample_clock_split import plan_verified_element_pcm_parts
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class PCMClockSplit(unittest.TestCase):
    def test_boundary_never_loses_or_duplicates_audio_frames(self):
        rate=24000;events=[{"job_id":str(i),"sample_frames":rate*80,
                             "sample_rate":rate} for i in range(1,5)]
        r=plan_verified_element_pcm_parts(clips=events,maximum_pcm_s=200)
        self.assertEqual(r["proposed_part_count"],2)
        self.assertEqual([len(x["events"]) for x in r["parts"]],[2,2])
        self.assertEqual([x["total_pcm_frames"] for x in r["parts"]],[rate*160]*2)
        self.assertFalse(r["actual_encoded_MP4_duration_verified"])
    def test_duplicate_and_unsplittable_elements_fail(self):
        e={"job_id":"a","sample_frames":24000,"sample_rate":24000}
        with self.assertRaises(FigureIdentityReviewRequired):
            plan_verified_element_pcm_parts(clips=[e,e])
        with self.assertRaises(FigureIdentityReviewRequired):
            plan_verified_element_pcm_parts(clips=[{"job_id":"a",
                "sample_frames":24000*121,"sample_rate":24000}])
