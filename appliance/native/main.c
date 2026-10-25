/* RedeTI Recovery OS - direct DRM/KMS single-screen LVGL prototype.
 * No X11, Wayland, Linux desktop, HTTP, Firefox or disk writes.
 * Requires an LVGL build with LV_USE_LINUX_DRM enabled plus json-c.
 * Prototype is NOT yet compiled or boot-validated against SystemRescue.
 */
#include <lvgl/lvgl.h>
#include <json-c/json.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NAVY  0x102437
extern const lv_image_dsc_t redeti_pd_logo;
/* Stable built-in fallback: custom lv_font_conv v1.5 glyphs were invisible
 * on LVGL 9. Keep labels legible until the custom font is raster-tested. */
static const lv_font_t *const redeti_text_font = &lv_font_montserrat_16;

/* Transliterate UTF-8 Portuguese accents to printable ASCII for the proven
 * built-in font. The diagnostic engine's JSON remains unchanged. */
static void safe_label_text(lv_obj_t *widget, const char *src) {
    char dst[1024];
    size_t w = 0;
    if (!src) src = "-";
    for (size_t i = 0; src[i] && w + 2 < sizeof dst;) {
        unsigned char x = (unsigned char)src[i];
        if (x < 128) {
            dst[w++] = (char)x;
            i++;
        } else if (x == 0xc3 && src[i + 1]) {
            unsigned char y = (unsigned char)src[i + 1];
            const char *replace = NULL;
            if (y >= 0x80 && y <= 0x86) replace = "A";
            else if (y == 0x87) replace = "C";
            else if (y >= 0x88 && y <= 0x8b) replace = "E";
            else if (y >= 0x8c && y <= 0x8f) replace = "I";
            else if (y == 0x91) replace = "N";
            else if (y >= 0x92 && y <= 0x98) replace = "O";
            else if (y >= 0x99 && y <= 0x9c) replace = "U";
            else if (y == 0x9d) replace = "Y";
            else if (y >= 0xa0 && y <= 0xa6) replace = "a";
            else if (y == 0xa7) replace = "c";
            else if (y >= 0xa8 && y <= 0xab) replace = "e";
            else if (y >= 0xac && y <= 0xaf) replace = "i";
            else if (y == 0xb1) replace = "n";
            else if (y >= 0xb2 && y <= 0xb8) replace = "o";
            else if (y >= 0xb9 && y <= 0xbc) replace = "u";
            else if (y >= 0xbd && y <= 0xbf) replace = "y";
            dst[w++] = replace ? *replace : '?';
            i += 2;
        } else {
            dst[w++] = '?';
            i++;
            while (((unsigned char)src[i] & 0xc0) == 0x80) i++;
        }
    }
    dst[w] = '\0';
    lv_label_set_text(widget, dst);
}
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
    safe_label_text(value, txt);
    lv_obj_set_style_text_font(value, redeti_text_font, 0);
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
/* The VPN bootstrap is independent from DRM; update status without HTTP. */
static void remote_status_update(lv_timer_t *timer) {
    lv_obj_t *widget = (lv_obj_t *)lv_timer_get_user_data(timer);
    json_object *state = json_object_from_file("/run/redeti/remote-status.json");
    if (!state) {
        safe_label_text(widget, "VPN: aguardando inicializacao  |  SSH: inativo");
        return;
    }
    const char *s = field_text(state, "state");
    if (strcmp(s, "connected") == 0) {
        char line[160];
        snprintf(line, sizeof(line), "VPN: conectada  |  SSH: paulo@%s",
                 field_text(state, "vpn_ip"));
        safe_label_text(widget, line);
    } else if (strcmp(s, "awaiting_provision") == 0) {
        safe_label_text(widget, "VPN: nao provisionada  |  SSH: protegido");
    } else if (strcmp(s, "connecting") == 0 || strcmp(s, "starting") == 0) {
        safe_label_text(widget, "VPN: conectando  |  SSH: aguardando autorizacao");
    } else {
        safe_label_text(widget, "VPN: indisponivel  |  SSH: inativo");
    }
    json_object_put(state);
}
/* LAN OpenSSH status is independent of the Tailscale enrollment status. */
static void lan_status_update(lv_timer_t *timer) {
    lv_obj_t *widget = (lv_obj_t *)lv_timer_get_user_data(timer);
    json_object *state = json_object_from_file("/run/redeti/lan-ssh-status.json");
    if (!state) {
        safe_label_text(widget, "SSH LAN: iniciando | usuario: paulo");
        return;
    }
    const char *s = field_text(state, "state");
    const char *ip = field_text(state, "lan_ip");
    char line[180];
    if (strcmp(s, "ready") == 0) {
        snprintf(line, sizeof line, "SSH LAN: paulo@%s | porta 22 | chave publica", ip);
    } else if (strcmp(s, "awaiting_key") == 0) {
        snprintf(line, sizeof line, "SSH LAN: %s | aguardando chave publica", ip);
    } else if (strcmp(s, "waiting_lan") == 0) {
        snprintf(line, sizeof line, "SSH LAN: aguardando rede | usuario: paulo");
    } else {
        snprintf(line, sizeof line, "SSH LAN: indisponivel | usuario: paulo");
    }
    safe_label_text(widget, line);
    json_object_put(state);
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
    lv_obj_set_style_text_font(root, redeti_text_font, 0);
    lv_obj_set_flex_flow(root, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_scroll_dir(root, LV_DIR_VER);
    lv_obj_set_scrollbar_mode(root, LV_SCROLLBAR_MODE_OFF);

    lv_obj_t *header = lv_obj_create(root);
    panel(header, NAVY);
    lv_obj_set_width(header, lv_pct(100));
    lv_obj_set_height(header, 92);
    lv_obj_set_flex_flow(header, LV_FLEX_FLOW_ROW);
    lv_obj_set_style_pad_column(header, 18, 0);
    lv_obj_t *mark = lv_image_create(header);
    lv_image_set_src(mark, &redeti_pd_logo);
    lv_obj_t *name = lv_obj_create(header);
    panel(name, NAVY);
    lv_obj_set_flex_grow(name, 1);
    lv_obj_set_height(name, 76);
    lv_obj_set_flex_flow(name, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_style_pad_row(name, 6, 0);
    lv_obj_t *headline = lv_label_create(name);
    lv_label_set_text(headline, "RedeTI Recovery OS");
    lv_obj_set_style_text_color(headline, lv_color_hex(WHITE), 0);
    lv_obj_set_style_text_font(headline, &lv_font_montserrat_28, 0);
    label(name, "DIAGNOSTICO AUTOMATICO  |  SOMENTE LEITURA", CYAN);
    label(root, "v0.5.3  |  Diagnóstico automático  |  SSH LAN + VPN", CYAN);
    lv_obj_t *remote_status = lv_label_create(root);
    lv_obj_set_width(remote_status, lv_pct(100));
    lv_obj_set_style_text_color(remote_status, lv_color_hex(CYAN), 0);
    lv_obj_set_style_text_font(remote_status, redeti_text_font, 0);
    safe_label_text(remote_status, "VPN: aguardando  |  SSH: inativo");
    lv_timer_t *remote_timer = lv_timer_create(remote_status_update, 2500, remote_status);
    remote_status_update(remote_timer);
    lv_obj_t *lan_status = lv_label_create(root);
    lv_obj_set_width(lan_status, lv_pct(100));
    lv_obj_set_style_text_color(lan_status, lv_color_hex(CYAN), 0);
    lv_obj_set_style_text_font(lan_status, redeti_text_font, 0);
    safe_label_text(lan_status, "SSH LAN: iniciando | usuario: paulo");
    lv_timer_t *lan_timer = lv_timer_create(lan_status_update, 2500, lan_status);
    lan_status_update(lan_timer);
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

    /* Show detected disks and partitions in the screen, not in a terminal. */
    label(root, "Hardware e particoes detectados automaticamente", WHITE);
    lv_obj_t *volumes = lv_obj_create(root);
    panel(volumes, PANEL);
    lv_obj_set_width(volumes, lv_pct(100));
    lv_obj_set_height(volumes, LV_SIZE_CONTENT);
    lv_obj_set_flex_flow(volumes, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_style_pad_row(volumes, 7, 0);
    json_object *disks = field_json(hardware, "disks");
    size_t count = disks && json_object_is_type(disks, json_type_array)
                       ? json_object_array_length(disks) : 0;
    if (count == 0) label(volumes, "Nenhum disco interno identificado nesta sessao", MUTED);
    for (size_t i = 0; i < count && i < 4; i++) {
        json_object *disk = json_object_array_get_idx(disks, i);
        if (!disk) continue;
        json_object *bytes = field_json(disk, "size_bytes");
        double gib = bytes && json_object_is_type(bytes, json_type_int)
                         ? (double)json_object_get_int64(bytes) / 1073741824.0 : 0.0;
        char text[400];
        snprintf(text, sizeof(text), "%s  |  %s  |  %.1f GiB  |  %s%s",
                 field_text(disk, "device"), field_text(disk, "model"), gib,
                 field_text(disk, "transport"),
                 json_object_get_boolean(field_json(disk, "is_removable_or_usb"))
                    ? "  |  USB/RECOVERY" : "");
        label(volumes, text, CYAN);
        json_object *parts = field_json(disk, "partitions");
        size_t pn = parts && json_object_is_type(parts, json_type_array)
                        ? json_object_array_length(parts) : 0;
        for (size_t j = 0; j < pn && j < 6; j++) {
            json_object *part = json_object_array_get_idx(parts, j);
            if (!part) continue;
            json_object *psize = field_json(part, "size_bytes");
            double pgib = psize && json_object_is_type(psize, json_type_int)
                              ? (double)json_object_get_int64(psize) / 1073741824.0 : 0.0;
            snprintf(text, sizeof(text), "   %s  |  %s  |  %.2f GiB",
                     field_text(part, "device"), field_text(part, "filesystem"), pgib);
            label(volumes, text, MUTED);
        }
        if (pn > 6) label(volumes, "   Mais particoes omitidas nesta tela", MUTED);
    }
    if (count > 4) label(volumes, "Mais discos detectados (resumo limitado a quatro)", MUTED);
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
