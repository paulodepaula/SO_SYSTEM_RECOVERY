"""Keep Brazilian Portuguese glyphs embedded in the direct DRM/KMS UI."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class NativeFontTests(unittest.TestCase):
    def test_pt_br_font_pipeline(self):
        cmake = (ROOT / "appliance/native/CMakeLists.txt").read_text()
        self.assertIn("lv_font_conv@1.5.3", cmake)
        self.assertIn("--range 0x20-0xFF", cmake)
        self.assertIn('redeti_font_16.c', cmake)
        self.assertIn('PTBR_FONT_SOURCE', cmake)
        self.assertIn('REDETI_FONT_TTF', cmake)

    def test_ui_uses_generated_font(self):
        main = (ROOT / "appliance/native/main.c").read_text()
        self.assertIn("LV_FONT_DECLARE(redeti_font_16);", main)
        self.assertIn("lv_obj_set_style_text_font(value, &redeti_font_16, 0);", main)
        self.assertIn("lv_obj_set_style_text_font(root, &redeti_font_16, 0);", main)

    def test_hardware_labels_remain_portuguese(self):
        main = (ROOT / "appliance/native/main.c").read_text()
        self.assertIn("Memória RAM", main)
        self.assertIn("Modo de inicialização", main)
        self.assertIn("Discos e partições", main)
        self.assertIn("Relatório técnico", main)
        self.assertIn("v0.5.1", main)
        self.assertIn("PT-BR: á é í ó ú ã õ ç", main)

if __name__ == "__main__":
    unittest.main()
