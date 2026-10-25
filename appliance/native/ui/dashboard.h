#ifndef REDETI_DASHBOARD_H
#define REDETI_DASHBOARD_H
#include <lvgl/lvgl.h>
#include <json-c/json.h>
/* Native first MVP. Never runs shell or disk repair actions. */
void redeti_dashboard_create(lv_display_t *display, json_object *hardware);
#endif
