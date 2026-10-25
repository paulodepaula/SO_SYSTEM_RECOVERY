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
        self.assertIn("width>=1180?420:width>=960?340:275", DASHBOARD)
        self.assertIn('?"Online":', DASHBOARD)
        self.assertIn('"Sem VPN"', DASHBOARD)
        self.assertIn("lv_obj_remove_flag(b,LV_OBJ_FLAG_CLICKABLE)", DASHBOARD)
        self.assertIn("lv_obj_set_style_bg_color(b,lv_color_hex(0x10293f),LV_STATE_DISABLED)", DASHBOARD)

    def test_premium_visuals_are_offline_and_native(self):
        theme=(ROOT/"appliance/native/ui/theme.c").read_text()
        art=(ROOT/"appliance/native/premium_assets.py").read_text()
        self.assertIn("ui/theme.c",CMAKE)
        self.assertIn("PREMIUM_SOURCE",CMAKE)
        self.assertIn("render-mvp-1366x768",CMAKE)
        for helper in ("redeti_theme_gradient", "redeti_theme_glow", "redeti_theme_active"):
            self.assertIn(helper,theme)
        self.assertIn("lv_image_set_src(illustration,&redeti_hero_laptop)",DASHBOARD)
        self.assertIn("lv_image_set_scale(illustration,scale)",DASHBOARD)
        self.assertIn("ICON_FOR(LV_SYMBOL_HOME,home)",DASHBOARD)
        self.assertIn("redeti_icon_home",(ROOT/"appliance/native/ui/assets.h").read_text())
        self.assertIn("lv_obj_set_style_image_recolor",DASHBOARD)
        self.assertIn("LV_COLOR_FORMAT_ARGB8888",art)
        self.assertIn("Image.Resampling.LANCZOS",art)
        for forbidden in ("requests.get", "urllib.request", "http://", "https://", "mount(", "os.system"):
            self.assertNotIn(forbidden,art)

    def test_status_panel_has_three_aligned_columns(self):
        self.assertIn('static void status_row3(',DASHBOARD)
        self.assertIn('flex(statusgrid,LV_FLEX_FLOW_COLUMN,2)',DASHBOARD)
        self.assertIn('const int row_width=half-24',DASHBOARD)
        self.assertIn('const int centre_w=row_width-20-18-label_w-detail_w',DASHBOARD)
        self.assertIn('lv_obj_set_style_text_align(*detail,LV_TEXT_ALIGN_RIGHT,0)',DASHBOARD)
        self.assertIn('lv_label_set_long_mode(*state,LV_LABEL_LONG_DOT)',DASHBOARD)
        self.assertIn('lv_label_set_long_mode(*detail,LV_LABEL_LONG_DOT)',DASHBOARD)
        self.assertIn('bool stack_mid=mainw<900',DASHBOARD)
        for title in ('"Rede"','"SSH"','"VPN"','"Entrada"'):
            self.assertIn(title,DASHBOARD)
        self.assertEqual(DASHBOARD.count('status_row3(statusgrid,row_width,'),4)
        self.assertNotIn('status_tile(',DASHBOARD)

    def test_status_values_and_colours_are_derived_from_real_state(self):
        self.assertIn('have_lan?"Conectada (LAN)":"Sem rede"',DASHBOARD)
        self.assertIn('ssh_ready?"Protegido"',DASHBOARD)
        self.assertIn('vpn_ready?"Conectada"',DASHBOARD)
        self.assertIn('str(vpn,"vpn_ip")',DASHBOARD)
        self.assertIn('status_indicator(s_status_lan_dot,have_lan?C_MINT',DASHBOARD)
        self.assertIn('status_indicator(s_status_ssh_dot,ssh_ready?C_MINT',DASHBOARD)
        self.assertIn('status_indicator(s_status_vpn_dot,vpn_ready?C_MINT',DASHBOARD)
        self.assertIn('redeti_input_start(display,s_group,s_input_state,s_input_detail,s_input_dot)',DASHBOARD)
        self.assertNotIn('192.168.1.100',DASHBOARD)

    def test_dashboard_exposes_source_revision_for_qemu_homologation(self):
        self.assertIn('REDETI_BUILD_REV',CMAKE)
        self.assertIn('COMMAND git rev-parse HEAD',CMAKE)
        self.assertIn('string(SUBSTRING "${REDETI_SOURCE_REV}" 0 8 REDETI_BUILD_REV)',CMAKE)
        self.assertIn('message(FATAL_ERROR "Recovery UI source revision must be a complete 40-character Git SHA")',CMAKE)
        self.assertNotIn('set(REDETI_BUILD_REV "unknown")',CMAKE)
        self.assertIn('target_compile_definitions(redeti-ui PRIVATE REDETI_BUILD_REV=',CMAKE)
        self.assertIn('txt(ver,REDETI_APP_VERSION,16,C_WHITE)',DASHBOARD)
        self.assertIn('txt(ver,REDETI_BUILD_TAG,14,C_CYAN)',DASHBOARD)
        self.assertIn('txt(ver,REDETI_BUILD_REV,14,C_MUTED)',DASHBOARD)
        self.assertNotIn('txt(ver,"DRM",14,C_CYAN)',DASHBOARD)
        self.assertNotIn('txt(ver,"v0.6.0"',DASHBOARD)
        self.assertNotIn('#define REDETI_BUILD_REV "unknown"',DASHBOARD)
        self.assertIn('project(redeti_recovery_appliance VERSION 0.6.0 LANGUAGES C)',CMAKE)
        self.assertIn('string(TIMESTAMP REDETI_BUILD_UTC "%y%m%d-%H%M%S" UTC)',CMAKE)
        self.assertIn('REDETI_BUILD_TAG="\u0024{REDETI_BUILD_TAG}"',CMAKE)
        self.assertIn('REDETI_APP_VERSION="v\u0024{PROJECT_VERSION}"',CMAKE)
        self.assertIn('lv_obj_set_size(ver,140,70)',DASHBOARD)

    def test_hero_uses_pinned_user_png_and_one_embedded_symbol(self):
        import hashlib
        import struct
        hero=ROOT/"appliance/native/assets/source/hero-laptop-panel.png"
        binary=hero.read_bytes()
        self.assertEqual(binary[:8],b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II",binary[16:24]),(380,197))
        self.assertEqual(hashlib.sha256(binary).hexdigest(),
                         "0a6e4edf7e152f8e8a99f503af770f6812c320cffef9cb6b095f2cfb5246a2ff")
        generator=(ROOT/"appliance/native/premium_assets.py").read_text()
        self.assertIn('"assets/source/hero-laptop-panel.png"',generator)
        self.assertIn('original.convert("RGBA")',generator)
        self.assertEqual(generator.count('emit_image("hero_laptop"'),1)
        self.assertNotIn('def laptop()',generator)
        self.assertIn('"${CMAKE_CURRENT_LIST_DIR}/assets/source/hero-laptop-panel.png"',CMAKE)
        self.assertIn('lv_image_set_src(illustration,&redeti_hero_laptop)',DASHBOARD)
        self.assertIn('(width-12)*256U/380U',DASHBOARD)

    def test_reference_quick_actions_use_three_by_two_grid(self):
        self.assertIn('int aq=(half-24-16)/3',DASHBOARD)
        self.assertIn('lv_obj_set_size(actions,lv_pct(100),160)',DASHBOARD)
        self.assertIn('lv_obj_set_size(tile,width,69)',DASHBOARD)
        self.assertEqual(DASHBOARD.count('quick_action_tile(actions,'),6)
        self.assertIn('quick_action_tile(actions,"Inventario"',DASHBOARD)
        self.assertIn('quick_action_tile(actions,"Hardware"',DASHBOARD)
        self.assertIn('quick_action_tile(actions,"Discos"',DASHBOARD)
        self.assertIn('quick_action_tile(actions,"Reparo do Windows"',DASHBOARD)
        self.assertIn('lv_obj_add_state(tile,LV_STATE_DISABLED)',DASHBOARD)
        self.assertIn('redeti_theme_quick_tile(tile,available)',DASHBOARD)
        self.assertNotIn('Reference layout: two equal columns',DASHBOARD)

    def test_scrollbar_has_dedicated_gutter_and_cards_fit(self):
        theme=(ROOT/"appliance/native/ui/theme.c").read_text()
        header=(ROOT/"appliance/native/ui/theme.h").read_text()
        self.assertIn('int mainw=viewportw-scroll_gutter',DASHBOARD)
        self.assertIn('lv_obj_set_style_pad_right(content,scroll_gutter,0)',DASHBOARD)
        self.assertIn('redeti_theme_scrollbar(content)',DASHBOARD)
        self.assertIn('LV_PART_SCROLLBAR',theme)
        self.assertIn('void redeti_theme_scrollbar(',header)
        self.assertIn('void redeti_theme_quick_tile(',header)
        self.assertIn('txt(b,name,14,active?C_WHITE:C_MUTED)',DASHBOARD)
        self.assertIn('txt(left,"Verificacao rapida de hardware, disco, sistema e rede.",14,C_MUTED)',DASHBOARD)

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
