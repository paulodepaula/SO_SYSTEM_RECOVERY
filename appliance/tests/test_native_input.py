"""Native DRM/KMS mouse and keyboard regression checks.
No real /dev/input node is accessed in CI.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class NativeInputTests(unittest.TestCase):
    def test_evdev_enabled_for_native_os(self):
        config = (ROOT / "appliance/native/lv_conf.h").read_text()
        self.assertIn("#define LV_USE_EVDEV 1", config)
        self.assertIn("#define LV_USE_LINUX_DRM 1", config)
        self.assertIn("#define LV_USE_X11 0", config)
        self.assertIn("#define LV_USE_WAYLAND 0", config)

    def test_input_source_and_arch_compiler_dependency(self):
        cmake = (ROOT / "appliance/native/CMakeLists.txt").read_text()
        arch = (ROOT / "appliance/build/build-native-arch.sh").read_text()
        workflow = (ROOT / ".github/workflows/native-appliance.yml").read_text()
        self.assertIn("input.c", cmake)
        self.assertIn("libevdev", arch)
        self.assertIn("libevdev-dev", workflow)

    def test_hotplug_registers_pointer_keyboard_and_cursor(self):
        source = (ROOT / "appliance/native/input.c").read_text()
        self.assertIn("lv_evdev_discovery_start(on_input_found, NULL)", source)
        self.assertIn("lv_indev_set_display(indev, s_display)", source)
        self.assertIn("LV_EVDEV_TYPE_REL", source)
        self.assertIn("LV_EVDEV_TYPE_ABS", source)
        self.assertIn("LV_EVDEV_TYPE_KEY", source)
        self.assertIn("lv_indev_set_cursor", source)
        self.assertIn("lv_indev_set_group", source)
        self.assertIn("lv_indev_add_event_cb", source)
        self.assertNotIn('"/dev/input/event0"', source)

    def test_real_interactive_button_and_keyboard_group(self):
        main = (ROOT / "appliance/native/ui/dashboard.c").read_text()
        for expected in ("lv_button_create(parent)", "LV_EVENT_CLICKED",
                         "lv_group_add_obj(s_group,b)",
                         "redeti_input_start(display,s_group,s_input_state)",
                         "redeti_input_start(display,s_group,s_input_state)",
                         "TESTAR ENTRADA", "v0.6.0"):
            self.assertIn(expected, main)
        self.assertIn("Entrada OK: clique ou Enter", main)

    def test_panel_entry_state_is_compact_and_truthful(self):
        source=(ROOT/"appliance/native/input.c").read_text()
        self.assertIn('s_pointer_count && s_keyboard_count',source)
        self.assertIn('"Mouse e teclado detectados"',source)
        self.assertIn('"Mouse OK; teclado aguardando"',source)
        self.assertIn('"Teclado OK; mouse aguardando"',source)
        self.assertIn('"Entrada indisponivel"',source)
        self.assertNotIn('teste: clique ou Tab + Enter',source)

    def test_diagnostics_remain_read_only(self):
        main = (ROOT / "appliance/native/ui/dashboard.c").read_text()
        self.assertIn("Nenhum reparo foi executado", main)
        self.assertNotIn("system(", main)

if __name__ == "__main__":
    unittest.main()
