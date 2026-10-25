"""A known-good LVGL font is required until the PT-BR font is raster-tested."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class NativeFontTests(unittest.TestCase):
    def test_incompatible_font_not_linked(self):
        cmake = (ROOT / "appliance/native/CMakeLists.txt").read_text()
        self.assertNotIn("lv_font_conv@", cmake)
        self.assertNotIn("PTBR_FONT_SOURCE", cmake)
        self.assertIn('add_executable(redeti-ui main.c input.c "${LOGO_SOURCE}")', cmake)

    def test_all_ui_labels_use_proven_fallback(self):
        main = (ROOT / "appliance/native/main.c").read_text()
        self.assertIn("redeti_text_font = &lv_font_montserrat_16", main)
        self.assertIn("safe_label_text(value, txt)", main)
        self.assertIn("lv_obj_set_style_text_font(remote_status, redeti_text_font", main)
        self.assertNotIn("&redeti_font_16", main)
        self.assertIn("v0.5.4", main)

    def test_pt_br_data_is_transliterated_without_modifying_inventory(self):
        main = (ROOT / "appliance/native/main.c").read_text()
        self.assertIn("static void safe_label_text(", main)
        self.assertIn("0xc3", main)
        self.assertIn("lv_label_set_text(widget, dst)", main)
        self.assertIn('field_text(field_json(hardware, "target"), "message")', main)

if __name__ == "__main__":
    unittest.main()
