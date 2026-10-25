#ifndef REDETI_LV_CONF_H
#define REDETI_LV_CONF_H
/* Dedicated appliance display: DRM dumb buffers; no window server. */
/* Visual dashboard creates hundreds of widgets; LVGL's 64 KiB default
 * internal heap is insufficient and may abort GUI before drawing a frame.
 * Keep a bounded 4 MiB allocator, independent from DRM framebuffer memory. */
#define LV_MEM_SIZE (4 * 1024 * 1024)
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
