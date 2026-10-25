#ifndef REDETI_UI_THEME_H
#define REDETI_UI_THEME_H
#include <lvgl/lvgl.h>
#include <stdint.h>

/* Decorative styles only: do not change hitboxes, input or data sources. */
void redeti_theme_gradient(lv_obj_t *obj, uint32_t from, uint32_t to);
void redeti_theme_glow(lv_obj_t *obj, uint32_t color, uint8_t strength);
void redeti_theme_card(lv_obj_t *obj, uint32_t from, uint32_t to);
void redeti_theme_active(lv_obj_t *obj);
void redeti_theme_quick_tile(lv_obj_t *obj, bool enabled);
void redeti_theme_scrollbar(lv_obj_t *obj);

#endif
