#ifndef REDETI_LV_CONF_H
#define REDETI_LV_CONF_H
/* Dedicated appliance display: DRM dumb buffers; no window server. */
#define LV_COLOR_DEPTH 32
#define LV_COLOR_FORMAT_DEFAULT LV_COLOR_FORMAT_XRGB8888
#define LV_USE_LINUX_DRM 1
#define LV_LINUX_DRM_AUTO_BACKEND 0
#define LV_LINUX_DRM_BACKEND LV_LINUX_DRM_BACKEND_FBDEV
#define LV_USE_LINUX_FBDEV 0
#define LV_USE_SDL 0
#define LV_USE_WAYLAND 0
#define LV_USE_X11 0
#define LV_USE_OPENGLES 0
#define LV_USE_EVDEV 1  /* direct Linux /dev/input event devices: mouse, tablet, keyboard */
#define LV_FONT_MONTSERRAT_14 1
#define LV_FONT_MONTSERRAT_16 1
#define LV_FONT_MONTSERRAT_20 1
#define LV_FONT_MONTSERRAT_28 1
#define LV_USE_LOG 1
#define LV_LOG_LEVEL LV_LOG_LEVEL_WARN
#endif
