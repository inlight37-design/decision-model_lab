"""대비 공식과 보고 범위 검사. 기존 팔레트의 접근성 통과를 주장하지 않는다."""
import unittest
from tools.audit_design_contrast import BACKGROUNDS, FOREGROUNDS, audit, contrast


class ContrastTests(unittest.TestCase):
    def test_black_white(self):
        self.assertEqual(contrast("#000000", "#ffffff"), 21.0)
    def test_equal_color(self):
        self.assertEqual(contrast("#a0b0c0", "#a0b0c0"), 1.0)
    def test_symmetry(self):
        self.assertEqual(contrast("#33518c", "#fbfbfa"), contrast("#fbfbfa", "#33518c"))
    def test_known_unknown_failure(self):
        self.assertAlmostEqual(contrast("#7b8188", "#fbfbfa"), 3.7996, places=3)
        self.assertLess(contrast("#7b8188", "#fbfbfa"), 4.5)
    def test_invalid_color(self):
        for color in (None, "red", "#fff", "#ffffff00", "#GGGGGG"):
            with self.subTest(color=color), self.assertRaises(ValueError): contrast(color, "#ffffff")
    def test_all_pairs(self):
        tokens = [{"name": name, "value": {"light":"#000000", "dark":"#000000"}}
                  for name in FOREGROUNDS + BACKGROUNDS]
        rows = audit({"color":{"tokens":tokens}})
        self.assertEqual(len(rows), 66)
        self.assertTrue(all(not row["passes_normal_text"] for row in rows))


if __name__ == "__main__":
    unittest.main()
