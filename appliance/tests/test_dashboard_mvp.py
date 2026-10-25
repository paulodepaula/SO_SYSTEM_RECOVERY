"""MVP dashboard acceptance contracts; no hardware or network access."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
DASHBOARD=(ROOT/"appliance/native/ui/dashboard.c").read_text()
MAIN=(ROOT/"appliance/native/main.c").read_text()
CMAKE=(ROOT/"appliance/native/CMakeLists.txt").read_text()

class DashboardMVP(unittest.TestCase):
    def test_lvgl_heap_sized_for_visual_dashboard(self):
        config=(ROOT/"appliance/native/lv_conf.h").read_text()
        self.assertIn("#define LV_MEM_SIZE (4 * 1024 * 1024)",config)

    def test_is_native_and_modular(self):
        self.assertIn('ui/dashboard.c',CMAKE)
        self.assertIn('redeti_dashboard_create(display, hardware)',MAIN)
        self.assertIn('lv_linux_drm_create()',MAIN)
        for forbidden in ("firefox","--kiosk","http://127.0.0.1:8765","system(","mount "):
            self.assertNotIn(forbidden,DASHBOARD)

    def test_reference_regions_and_branded_hero(self):
        for section in ("header(root,sw)", "sidebar(side,compact)",
                        "hero(content,mainw", "data_card(stat",
                        "Status do Sistema", "Acoes Rapidas",
                        "Modulos de Diagnostico", "Discos e Particoes"):
            self.assertIn(section,DASHBOARD)
        self.assertIn("redeti_pd_logo",DASHBOARD)
        self.assertIn("laptop_art(area,laptop_width)",DASHBOARD)
        self.assertIn("stars(area,width,240)",DASHBOARD)

    def test_mid_size_display_keeps_laptop_and_short_vpn_status(self):
        self.assertIn("hero(content,mainw,mainw>=900)", DASHBOARD)
        self.assertIn("width>=1180?420:275", DASHBOARD)
        self.assertIn('?"Online":', DASHBOARD)
        self.assertIn('"Sem VPN"', DASHBOARD)
        self.assertIn("lv_obj_remove_flag(b,LV_OBJ_FLAG_CLICKABLE)", DASHBOARD)
        self.assertIn("lv_obj_set_style_bg_color(b,lv_color_hex(0x10293f),LV_STATE_DISABLED)", DASHBOARD)

    def test_real_state_and_no_placeholder_values(self):
        for source in ("hardware.json", "remote-status.json", "lan-ssh-status.json"):
            self.assertIn(source,MAIN+DASHBOARD)
        for source in ('"ram_bytes"','"recovery_boot_firmware"','"target"','"disks"'):
            self.assertIn(source,DASHBOARD)
        self.assertNotIn("192.168.1.100",DASHBOARD)
        self.assertNotIn("43%",DASHBOARD)
        self.assertIn("paulo@%s",DASHBOARD)
        self.assertIn('Nenhum reparo foi executado',DASHBOARD)

    def test_navigation_has_actual_callbacks(self):
        for method in ("clicked_test", "clicked_details","clicked_home",
                       "clicked_network","lv_obj_scroll_to_view",
                       "lv_obj_scroll_to_y","redeti_input_start("):
            self.assertIn(method,DASHBOARD)
        self.assertIn("lv_obj_add_state(b,LV_STATE_DISABLED)",DASHBOARD)
        self.assertIn("lv_group_add_obj(s_group,b)",DASHBOARD)

    def test_responsive_and_scrolling(self):
        self.assertIn("int sw=lv_display_get_horizontal_resolution(display)",DASHBOARD)
        self.assertIn("int sh=lv_display_get_vertical_resolution(display)",DASHBOARD)
        self.assertIn("compact=sw<1200, legacy=sw<900",DASHBOARD)
        self.assertIn("LV_FLEX_FLOW_ROW_WRAP",DASHBOARD)
        self.assertIn("LV_DIR_VER",DASHBOARD)

if __name__=="__main__":
    unittest.main()
