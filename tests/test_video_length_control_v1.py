"""Source-bound slide-group split policy regression."""
import pytest
from selenium_pipeline.video_length_control_v1 import plan

def test_greedy_slide_groups_remain_under_600s():
    wavs=[2.84,47.28,41.92,49.28,58.44,56.48,57.72,63.8,60.96,59.08,61.2,53.2,52.12]
    parts=plan(wavs)
    assert [(first+1,last) for first,last,_,_ in parts]==[(1,11),(12,13)]
    assert parts[0][2]==0.0
    assert round(parts[-1][3],2)==664.32
    assert sum(end-start for start,end,_,_ in parts)==len(wavs)
    assert all((x[3]-x[2])<600 for x in parts)

def test_reject_single_slide_exceeding_cap():
    with pytest.raises(ValueError):
        plan([25.,571.,4.])
    with pytest.raises(ValueError):
        plan([])
