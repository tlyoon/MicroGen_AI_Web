from pathlib import Path
import pymupdf
from selenium_pipeline.figure_slide_impact import restored_figure_impact
from selenium_pipeline.narration_repair_plan import plan_repair

def test_restored_figure_maps_to_frame(tmp_path):
    (tmp_path/"slides.tex").write_text(
        r"\begin{frame}First\end{frame}" + "\n" +
        r"\begin{frame}Second \includegraphics{figure.png}\end{frame}",
        encoding="utf-8")
    result=restored_figure_impact(tmp_path/"slides.tex",["figure.png"],2)
    assert result["affected"]==[2]
    assert not result["conservative_full_review"]

def test_overlay_falls_back_to_full_review(tmp_path):
    (tmp_path/"slides.tex").write_text(
        r"\begin{frame}\pause \includegraphics{figure.png}\end{frame}",
        encoding="utf-8")
    result=restored_figure_impact(tmp_path/"slides.tex",["figure.png"],2)
    assert result["affected"]==[1,2]
    assert result["conservative_full_review"]

def test_repair_plan_uses_latex_mapping(tmp_path):
    (tmp_path/"slides.tex").write_text(
        r"\begin{frame}First\end{frame}" + "\n" +
        r"\begin{frame}\includegraphics{figure.png}\end{frame}",
        encoding="utf-8")
    for name in ("previous.pdf","slides.pdf"):
        d=pymupdf.open()
        d.new_page()
        d.new_page()
        d.save(tmp_path/name)
        d.close()
    report=plan_repair(tmp_path,tmp_path/"previous.pdf",["figure.png"])
    assert report["affected"]==[2]
    assert report["impact_method"]=="latex_figure_reference_mapping"
    assert report["video_publication_allowed"] is False
