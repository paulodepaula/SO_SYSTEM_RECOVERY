/* RedeTI Recovery OS: minimal native DRM/KMS LVGL bootstrap.
 * No X11, Wayland, Linux desktop, browser, HTTP or disk modification.
 * Native interface lives in ui/dashboard.c. */
#include <lvgl/lvgl.h>
#include <json-c/json.h>
#include <stdio.h>
#include "ui/dashboard.h"

int main(int argc, char **argv)
{
    const char *snapshot = argc > 1 ? argv[1] : "/run/redeti/hardware.json";
    json_object *hardware = json_object_from_file(snapshot);
    if(!hardware) {
        fprintf(stderr, "RedeTI: inventario de hardware indisponivel.\n");
        return 2;
    }

    lv_init();
    lv_display_t *display = lv_linux_drm_create();
    if(!display) { json_object_put(hardware); return 3; }
    char *device = lv_linux_drm_find_device_path();
    if(!device) {
        fprintf(stderr, "RedeTI: dispositivo DRM/KMS indisponivel.\n");
        json_object_put(hardware);
        return 4;
    }
    lv_linux_drm_set_file(display, device, -1);
    lv_free(device);
    if(!lv_display_get_horizontal_resolution(display) ||
       !lv_display_get_vertical_resolution(display)) {
        fprintf(stderr, "RedeTI: modo DRM/KMS nao inicializado.\n");
        json_object_put(hardware);
        return 5;
    }
    redeti_dashboard_create(display, hardware);
    json_object_put(hardware);

    for(;;) {
        uint32_t delay=lv_timer_handler();
        lv_delay_ms(delay == LV_NO_TIMER_READY ? 15 : (delay < 5 ? 5 : delay));
    }
}
