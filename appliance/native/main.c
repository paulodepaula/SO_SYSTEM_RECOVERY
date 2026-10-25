/* RedeTI Recovery OS - direct DRM/KMS single-screen LVGL prototype.
 * No X11, Wayland, Linux desktop, HTTP, Firefox or disk writes.
 * Requires an LVGL build with LV_USE_LINUX_DRM enabled plus json-c.
 * Prototype is NOT yet compiled or boot-validated against SystemRescue.
 */
#include <lvgl/lvgl.h>
#include <json-c/json.h>
#include <stdio.h>
#include <stdlib.h>

#define NAVY  0x102437
#define PANEL 0x1b3045
#define CARD  0x233b51
#define CYAN  0x59b2ea
#define WHITE 0xe7f2fc
#define MUTED 0xa8bdcd

static json_object *field_json(json_object *root, const char *key) {
    json_object *value = NULL;
    if (root) json_object_object_get_ex(root, key, &value);
    return value;
}
static const char *field_text(json_object *root, const char *key) {
    json_object *value = field_json(root, key);
    return value && json_object_is_type(value, json_type_string) ?
        json_object_get_string(value) : "Não identificado";
}
static void panel(lv_obj_t *obj, uint32_t color) {
    lv_obj_set_style_bg_color(obj, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(obj, 0, 0);
    lv_obj_set_style_radius(obj, 12, 0);
    lv_obj_set_style_pad_all(obj, 12, 0);
}
static void label(lv_obj_t *parent, const char *txt, uint32_t color) {
    lv_obj_t *value = lv_label_create(parent);
    lv_label_set_text(value, txt ? txt : "-");
    lv_obj_set_style_text_color(value, lv_color_hex(color), 0);
    lv_obj_set_width(value, lv_pct(100));
    lv_label_set_long_mode(value, LV_LABEL_LONG_WRAP);
}
static void info_card(lv_obj_t *parent, const char *title, const char *text, int width) {
    lv_obj_t *card = lv_obj_create(parent);
    panel(card, CARD);
    lv_obj_set_width(card, width);
    lv_obj_set_height(card, 104);
    lv_obj_set_flex_flow(card, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_style_pad_row(card, 8, 0);
    label(card, title, MUTED);
    label(card, text, WHITE);
}
static void diagnostic_card(lv_obj_t *parent, const char *title, const char *status, int width) {
    lv_obj_t *card = lv_obj_create(parent);
    panel(card, PANEL);
    lv_obj_set_width(card, width);
    lv_obj_set_height(card, 118);
    lv_obj_set_flex_flow(card, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_style_pad_row(card, 10, 0);
    lv_obj_set_style_border_width(card, 1, 0);
    lv_obj_set_style_border_color(card, lv_color_hex(0x365269), 0);
    label(card, title, CYAN);
    label(card, status, MUTED);
}
static void build_ui(lv_display_t *display, json_object *hardware) {
    int screen_width = lv_display_get_horizontal_resolution(display);
    if (screen_width < 360) screen_width = 360;
    int cols = screen_width > 1000 ? 4 : (screen_width > 680 ? 2 : 1);
    int diagnostic_cols = screen_width > 1000 ? 3 : (screen_width > 680 ? 2 : 1);
    int col_width = (screen_width - 88 - 10 * (cols - 1)) / cols;
    int diag_width = (screen_width - 88 - 10 * (diagnostic_cols - 1)) / diagnostic_cols;
    lv_obj_t *root = lv_screen_active();
    panel(root, NAVY);
    lv_obj_set_style_radius(root, 0, 0);
    lv_obj_set_style_pad_all(root, 16, 0);
    lv_obj_set_style_pad_row(root, 14, 0);
    lv_obj_set_style_text_font(root, &lv_font_montserrat_16, 0);
    lv_obj_set_flex_flow(root, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_scroll_dir(root, LV_DIR_VER);

    label(root, "PD  RedeTI Recovery OS                 SOMENTE LEITURA", WHITE);
    label(root, "Central de diagnóstico  |  Reconhecimento automático", CYAN);
    lv_obj_t *summary = lv_obj_create(root);
    panel(summary, PANEL);
    lv_obj_set_width(summary, lv_pct(100));
    lv_obj_set_height(summary, LV_SIZE_CONTENT);
    lv_obj_set_flex_flow(summary, LV_FLEX_FLOW_ROW_WRAP);
    lv_obj_set_style_pad_row(summary, 10, 0);
    lv_obj_set_style_pad_column(summary, 10, 0);

    info_card(summary, "Processador", field_text(field_json(hardware, "cpu"), "model"), col_width);
    char ram[48] = "Não identificado";
    json_object *memory = field_json(hardware, "ram_bytes");
    if (memory && json_object_is_type(memory, json_type_int))
        snprintf(ram, sizeof(ram), "%.1f GiB", (double)json_object_get_int64(memory) / 1073741824.0);
    info_card(summary, "Memória RAM", ram, col_width);
    info_card(summary, "Modo de inicialização", field_text(hardware, "recovery_boot_firmware"), col_width);
    info_card(summary, "Disco e Windows", field_text(field_json(hardware, "target"), "message"), col_width);

    label(root, "Diagnósticos disponíveis", WHITE);
    lv_obj_t *grid = lv_obj_create(root);
    panel(grid, NAVY);
    lv_obj_set_width(grid, lv_pct(100));
    lv_obj_set_height(grid, LV_SIZE_CONTENT);
    lv_obj_set_flex_flow(grid, LV_FLEX_FLOW_ROW_WRAP);
    lv_obj_set_style_pad_row(grid, 10, 0);
    lv_obj_set_style_pad_column(grid, 10, 0);
    diagnostic_card(grid, "Discos e partições", "Inventário inicial coletado", diag_width);
    diagnostic_card(grid, "SMART / armazenamento", "Somente consulta; não iniciado", diag_width);
    diagnostic_card(grid, "EFI / BCD", "Módulo em desenvolvimento", diag_width);
    diagnostic_card(grid, "Arquivos Windows", "Módulo em desenvolvimento", diag_width);
    diagnostic_card(grid, "Registro e drivers", "Módulo em desenvolvimento", diag_width);
    diagnostic_card(grid, "Relatório técnico", "Módulo em desenvolvimento", diag_width);
    label(root, "Windows não confirmado apenas por NTFS. Nenhum reparo foi executado.", MUTED);
}
int main(int argc, char **argv) {
    const char *snapshot = argc > 1 ? argv[1] : "/run/redeti/hardware.json";
    json_object *hw = json_object_from_file(snapshot);
    if (!hw) {
        fprintf(stderr, "RedeTI: snapshot de hardware indisponível.\n");
        return 2;
    }
    lv_init();
    lv_display_t *display = lv_linux_drm_create();
    if (!display) { json_object_put(hw); return 3; }
    char *device = lv_linux_drm_find_device_path();
    if (!device) {
        fprintf(stderr, "RedeTI: display DRM/KMS indisponível.\n");
        json_object_put(hw);
        return 4;
    }
    lv_linux_drm_set_file(display, device, -1);
    lv_free(device);
    if (!lv_display_get_horizontal_resolution(display)) {
        fprintf(stderr, "RedeTI: DRM initialized without a usable display mode.\n");
        json_object_put(hw);
        return 5;
    }
    build_ui(display, hw);
    json_object_put(hw);
    while (1) {
        uint32_t next = lv_timer_handler();
        lv_delay_ms(next == LV_NO_TIMER_READY ? 15 : (next < 5 ? 5 : next));
    }
    return 0;
}
