/* Synthetic LVGL display smoke test: no DRM device, disks or client network.
 * The test exercises real widget allocations, event wiring and rasterization,
 * catching small default-heap crashes that a compile-only check cannot see.
 */
#include <lvgl/lvgl.h>
#include <json-c/json.h>
#include <stdio.h>
#include <stdlib.h>
#include "../ui/dashboard.h"
#include "../ui/assets.h"

static unsigned rendered;
static void flush(lv_display_t *d, const lv_area_t *area, uint8_t *pixels)
{
    (void)area;
    (void)pixels;
    ++rendered;
    lv_display_flush_ready(d);
}
int main(int argc, char **argv)
{
    int width=argc>1?atoi(argv[1]):1280;
    int height=argc>2?atoi(argv[2]):720;
    if(width<900||width>1920||height<720||height>1080) return 2;

    /* Catch stale procedural assets before certifying a new appliance. */
    if(redeti_hero_laptop.header.w!=380 || redeti_hero_laptop.header.h!=197) {
        fprintf(stderr,"Wrong hero asset dimensions; rebuild generated LVGL images.\\n");
        return 7;
    }
    lv_init();
    lv_display_t *d=lv_display_create(width,height);
    if(!d) return 3;
    /* Partial RGB8888 framebuffer only, 12 scanlines. */
    size_t bytes=(size_t)width*12*4;
    void *pixels=calloc(1,bytes);
    if(!pixels) return 4;
    lv_display_set_buffers(d,pixels,NULL,(uint32_t)bytes,LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(d,flush);

    /* All simulated data; no lsblk, mounts, network or actual hardware. */
    json_object *hw=json_tokener_parse(
        "{\"cpu\":{\"model\":\"QEMU TEST CPU\"},\"ram_bytes\":8589934592,"
        "\"recovery_boot_firmware\":\"UEFI\","
        "\"target\":{\"message\":\"Nenhum Windows confirmado\"},"
        "\"disks\":[]}");
    if(!hw) return 5;
    redeti_dashboard_create(d,hw);
    for(int i=0;i<12;i++){
        lv_tick_inc(30);
        lv_timer_handler();
    }
    printf("UI smoke: %dx%d, flushes=%u\n",width,height,rendered);
    json_object_put(hw);
    return rendered>0?0:6;
}
