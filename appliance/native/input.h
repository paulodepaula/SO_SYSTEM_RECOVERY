#ifndef REDETI_INPUT_H
#define REDETI_INPUT_H
#include "lvgl/lvgl.h"
/* Register Linux evdev pointer and keyboard, with hotplug, on DRM display.
 * Diagnostics remain in read-only mode; input registration never writes disks.
 */
bool redeti_input_start(lv_display_t *display, lv_group_t *keys, lv_obj_t *status);
#endif
