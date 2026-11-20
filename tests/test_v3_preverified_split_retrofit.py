"""Historical vector panel and preverified source-ledger retrofit guards."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
from selenium_pipeline.retrofit_image_repair import (
    bootstrap_legacy_source_figures,patch_files)
from selenium_pipeline.source_split_figure_chain_v1 import _prove_coverage,FigureChainError

class PatchGuards(unittest.TestCase):
 def test_explicit_source_evidence_json_allowed(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   (root/'slides.tex').write_text('corrected')
   for name in ('source_figure_chain_v1.json',
                'source_split_figure_chain_v1.json',
                'figure_repair_provenance.json'):
    (root/name).write_text('{}')
   self.assertEqual(len(patch_files(root)),4)

 def test_unauthorized_json_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   (root/'slides.tex').write_text('corrected')
   (root/'stale_completion.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'Unsafe'):patch_files(root)

class PreverifiedReceipt(unittest.TestCase):
 def test_sha_and_panel_checks_required_even_when_ledger_provided(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   (root/'source.pdf').write_bytes(b'%PDF-real-file')
   (root/'source_figure_chain_v1.json').write_text('{}')
   (root/'source_split_figure_chain_v1.json').write_text('{}')
   with patch('selenium_pipeline.source_caption_figure_chain_v1.has_real_pdf_header',return_value=True), \
        patch('selenium_pipeline.source_caption_figure_chain_v1.printed_source_captions',return_value=[{'id':'8.7'}]), \
        patch('selenium_pipeline.source_caption_figure_chain_v1.verify_figure_crops',return_value={'figure_count':1,'status':'ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED'}), \
        patch('selenium_pipeline.source_caption_figure_chain_v1.verify_latex_figure_chain',return_value={'figures_verified':1,'source_sha256':'SHA'}), \
        patch('selenium_pipeline.source_split_figure_chain_v1.verify_split_figure_chain',side_effect=FigureChainError('missing source panel')) as verifier:
    with self.assertRaisesRegex(FigureChainError,'missing source panel'):
     bootstrap_legacy_source_figures(root)
    verifier.assert_called_once()

 def test_verified_ledger_is_reused_without_heuristic_cropping(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   (root/'source.pdf').write_bytes(b'%PDF-file')
   (root/'source_figure_chain_v1.json').write_text('{}')
   with patch('selenium_pipeline.source_caption_figure_chain_v1.has_real_pdf_header',return_value=True), \
        patch('selenium_pipeline.source_caption_figure_chain_v1.printed_source_captions',return_value=[{'id':'8.10'}]), \
        patch('selenium_pipeline.source_caption_figure_chain_v1.verify_figure_crops',return_value={'figure_count':1,'status':'ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED'}), \
        patch('selenium_pipeline.source_caption_figure_chain_v1.verify_latex_figure_chain',return_value={'figures_verified':1,'source_sha256':'originalSHA'}), \
        patch('selenium_pipeline.source_caption_figure_chain_v1.recover_printed_source_figures',side_effect=AssertionError('unsafe guess')):
    outcome=bootstrap_legacy_source_figures(root)
    self.assertEqual(outcome['recovery_status'],'ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED')
    self.assertTrue(outcome['preverified_source_ledger_reused'])

class VectorSplitGuards(unittest.TestCase):
 class FakePage:
  def __init__(self,letters):
   self.letters=letters
  def get_image_info(self,**kwargs):return []
  def get_drawings(self):
   return [{'rect':(21+i,60,24+i,199)} for i in range(20)]
  def get_text(self,which):
   if which=='words':
    out=[]
    if 'a' in self.letters:out.append((42,100,45,110,'a'))
    if 'b' in self.letters:out.append((42,240,45,250,'b'))
    return out

 def test_vector_union_preserves_two_lettered_panels(self):
  page=self.FakePage({'a','b'})
  rects=[fitz.Rect(20,50,170,198),fitz.Rect(20,198,170,350)]
  result=_prove_coverage(page,fitz.Rect(20,50,170,350),rects)
  self.assertEqual(result['source_vector_panel_count'],2)
  self.assertEqual(result['source_vector_panel_labels'],['a','b'])

 def test_missing_second_letter_blocks_split(self):
  page=self.FakePage({'a'})
  with self.assertRaises(FigureChainError):
   _prove_coverage(page,fitz.Rect(20,50,170,350),
                   [fitz.Rect(20,50,170,198),fitz.Rect(20,198,170,350)])

if __name__=='__main__':unittest.main()
