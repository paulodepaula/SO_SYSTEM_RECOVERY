/* RedeTI Recovery OS premium palette; no runtime assets or filesystem reads. */
#include "theme.h"

void redeti_theme_gradient(lv_obj_t *obj, uint32_t from, uint32_t to)
{
    lv_obj_set_style_bg_color(obj, lv_color_hex(from), 0);
    lv_obj_set_style_bg_grad_color(obj, lv_color_hex(to), 0);
    lv_obj_set_style_bg_grad_dir(obj, LV_GRAD_DIR_VER, 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
}

void redeti_theme_glow(lv_obj_t *obj, uint32_t color, uint8_t strength)
{
    lv_obj_set_style_shadow_color(obj, lv_color_hex(color), 0);
    lv_obj_set_style_shadow_width(obj, 12, 0);
    lv_obj_set_style_shadow_spread(obj, 1, 0);
    lv_obj_set_style_shadow_opa(obj, strength, 0);
}

void redeti_theme_card(lv_obj_t *obj, uint32_t from, uint32_t to)
{
    redeti_theme_gradient(obj, from, to);
    lv_obj_set_style_border_color(obj, lv_color_hex(0x28536f), 0);
    lv_obj_set_style_border_width(obj, 1, 0);
    redeti_theme_glow(obj, 0x0072b5, 24);
}

void redeti_theme_active(lv_obj_t *obj)
{
    redeti_theme_gradient(obj, 0x0869b6, 0x063e79);
    lv_obj_set_style_border_color(obj, lv_color_hex(0x2ecbff), 0);
    lv_obj_set_style_border_width(obj, 1, 0);
    redeti_theme_glow(obj, 0x00baff, 66);
}
