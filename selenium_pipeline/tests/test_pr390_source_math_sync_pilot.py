"""Source math substitution identity and independently decoded pixel guards."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from selenium_pipeline.original_source_math_sync_pilot import equation_key
from selenium_pipeline.original_math_sync_video_verify import count_yellow_border

SOURCE_TAN="a2 + x2 = a2 + a2 tan2 u = a2(1 + tan2 u) = a2 sec2 u."
SOURCE_SIN="a2 - x2 = a2 - a2 sin2 u = a2(1 - sin2 u) = a2 cos2 u."
SLIDE_TAN="a2 + x2 = a2 + a2 tan2 θ = a2(1 + tan2 θ) = a2 sec2 θ"
SLIDE_SIN="a2 −x2 = a2 −a2 sin2 θ = a2(1 −sin2 θ) = a2 cos2 θ"

class TestOriginalSourceMathSync(unittest.TestCase):
    def test_independent_complete_textbook_chain_equivalence(self):
        self.assertEqual(equation_key(SOURCE_TAN),equation_key(SLIDE_TAN))
        self.assertEqual(equation_key(SOURCE_SIN),equation_key(SLIDE_SIN))

    def test_operator_and_function_corruptions_not_equivalent(self):
        self.assertNotEqual(equation_key(SOURCE_TAN),
                            equation_key(SLIDE_TAN.replace("sec2","cos2")))
        self.assertNotEqual(equation_key(SOURCE_SIN),
                            equation_key(SLIDE_SIN.replace("−a2"," +a2")))

    def test_no_incorrect_automatic_equation_sign_approval(self):
        self.assertNotEqual(equation_key(SOURCE_SIN),equation_key(SLIDE_TAN))
        self.assertNotEqual(equation_key("a2+x2=a2sec2u"),
                            equation_key("a2-x2=a2sec2θ"))

    def test_decode_border_probes_distinguish_highlight(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"frame.png"
            image=Image.new("RGB",(400,240),(245,245,245))
            rect=[40.,40.,150.,60.]
            self.assertTrue(count_yellow_border_from_image(image,path,rect)==0)
            draw=ImageDraw.Draw(image)
            draw.rectangle((int(rect[0]*2)-4,int(rect[1]*2)-4,
                            int(rect[2]*2)+4,int(rect[3]*2)+4),
                           outline=(255,235,0),width=4)
            image.save(path)
            self.assertEqual(count_yellow_border(path,rect),8)

def count_yellow_border_from_image(image,path,rect):
    image.save(path)
    return count_yellow_border(path,rect)

if __name__=="__main__":
    unittest.main()
