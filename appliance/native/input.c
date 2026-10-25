/* RedeTI Recovery OS: native input for DRM/KMS (no X11, desktop, HTTP).
 * Uses LVGL 9.6 evdev device discovery instead of hard-coded eventN paths.
 */
#include "input.h"
#include <stdio.h>

static lv_display_t *s_display;
static lv_group_t *s_keys;
static lv_obj_t *s_status;
static lv_obj_t *s_detail;
static lv_obj_t *s_indicator;
static unsigned s_pointer_count;
static unsigned s_keyboard_count;

static void update_status(void)
{
    if(s_status==NULL)return;
    /* The EVDEV counts come from actual device discovery and hotplug. */
    bool mouse=s_pointer_count>0, keyboard=s_keyboard_count>0;
    const char *state=mouse&&keyboard?"Mouse + teclado EVDEV":
                      mouse?"Mouse EVDEV":keyboard?"Teclado EVDEV":
                      "Aguardando EVDEV";
    const char *result=mouse&&keyboard?"OK":
                       mouse||keyboard?"Parcial":"-";
    lv_label_set_text(s_status,state);
    if(s_detail)lv_label_set_text(s_detail,result);
    if(s_indicator)lv_obj_set_style_bg_color(
        s_indicator,lv_color_hex(mouse&&keyboard?0x0fd2b5:
                                 mouse||keyboard?0xf8b935:0x7894ad),0);
}

static void delete_cursor(lv_event_t *e)
{
    lv_obj_t *cursor = lv_event_get_user_data(e);
    if(cursor) lv_obj_delete(cursor);
    if(s_pointer_count) s_pointer_count--;
    update_status();
}

static void keyboard_deleted(lv_event_t *e)
{
    (void)e;
    if(s_keyboard_count) s_keyboard_count--;
    update_status();
}

static void on_input_found(lv_indev_t *indev, lv_evdev_type_t type, void *data)
{
    (void)data;
    /* The pinned LVGL 9.6 evdev discovery needs a non-NULL callback. */
    lv_indev_set_display(indev, s_display);
    if(type == LV_EVDEV_TYPE_KEY) {
        lv_indev_set_group(indev, s_keys);
        lv_indev_add_event_cb(indev, keyboard_deleted, LV_EVENT_DELETE, NULL);
        s_keyboard_count++;
    } else if(type == LV_EVDEV_TYPE_REL || type == LV_EVDEV_TYPE_ABS) {
        /* lv_evdev handles REL deltas and obtains ABS calibration from ioctl
         * for USB Tablet devices. No hard-coded QEMU resolution. */
        lv_obj_t *cursor = lv_obj_create(lv_layer_sys());
        lv_obj_set_size(cursor, 16, 16);
        lv_obj_set_style_radius(cursor, 2, 0);
        lv_obj_set_style_bg_color(cursor, lv_color_hex(0x59b2ea), 0);
        lv_obj_set_style_bg_opa(cursor, LV_OPA_COVER, 0);
        lv_obj_set_style_border_color(cursor, lv_color_hex(0xffffff), 0);
        lv_obj_set_style_border_width(cursor, 2, 0);
        lv_obj_set_style_pad_all(cursor, 0, 0);
        lv_obj_remove_flag(cursor, LV_OBJ_FLAG_CLICKABLE);
        lv_indev_set_cursor(indev, cursor);
        lv_indev_add_event_cb(indev, delete_cursor, LV_EVENT_DELETE, cursor);
        s_pointer_count++;
    }
    update_status();
}

bool redeti_input_start(lv_display_t *display, lv_group_t *keys,
                        lv_obj_t *status, lv_obj_t *detail, lv_obj_t *indicator)
{
    s_display = display;
    s_keys = keys;
    s_status = status;
    s_detail = detail;
    s_indicator = indicator;
    s_pointer_count = 0;
    s_keyboard_count = 0;
    update_status();
    /* Discovery scans /dev/input/event* now and follows USB hotplug. */
    lv_result_t result = lv_evdev_discovery_start(on_input_found, NULL);
    if(result != LV_RESULT_OK) {
        lv_label_set_text(status, "Entrada indisponivel");
        if(s_detail)lv_label_set_text(s_detail,"-");
        if(s_indicator)lv_obj_set_style_bg_color(
            s_indicator,lv_color_hex(0x7894ad),0);
        fprintf(stderr, "RedeTI: EVDEV discovery failed (no mouse/keyboard).\n");
        return false;
    }
    return true;
}
