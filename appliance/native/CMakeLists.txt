cmake_minimum_required(VERSION 3.20)
project(redeti_recovery_appliance VERSION 0.5 LANGUAGES C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
include(FetchContent)
find_package(PkgConfig REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_program(NPM_EXECUTABLE NAMES npm REQUIRED)
find_file(REDETI_FONT_TTF NAMES DejaVuSans.ttf
  PATHS /usr/share/fonts/TTF /usr/share/fonts/truetype/dejavu
  REQUIRED)
pkg_check_modules(DRM REQUIRED IMPORTED_TARGET libdrm)
pkg_check_modules(JSONC REQUIRED IMPORTED_TARGET json-c)

# Reproducible upstream LVGL v9.6.0 revision; no floating master.
set(LVGL_COMMIT "80ca777e37a2b176770726a02e07a6fb79ef0b39")
set(LV_BUILD_CONF_PATH "${CMAKE_CURRENT_LIST_DIR}/lv_conf.h" CACHE FILEPATH "RedeTI LVGL config" FORCE)
set(LV_BUILD_SET_CONFIG_OPTS ON CACHE BOOL "" FORCE)
set(LV_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LV_BUILD_DEMOS OFF CACHE BOOL "" FORCE)
FetchContent_Declare(lvgl GIT_REPOSITORY https://github.com/lvgl/lvgl.git GIT_TAG "${LVGL_COMMIT}" GIT_SHALLOW FALSE)
FetchContent_MakeAvailable(lvgl)

set(LOGO_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/logo_pd.c")
add_custom_command(
  OUTPUT "${LOGO_SOURCE}"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/generate_logo.py"
    "${CMAKE_CURRENT_LIST_DIR}/../../assets/logo-paulo.svg" "${LOGO_SOURCE}"
  DEPENDS "${CMAKE_CURRENT_LIST_DIR}/generate_logo.py"
          "${CMAKE_CURRENT_LIST_DIR}/../../assets/logo-paulo.svg"
  COMMENT "Converting original PD logo to native LVGL RGB565"
)
# Stock Montserrat fonts only cover ASCII. Generate a compact UTF-8 font
# with Latin-1 accents for Brazilian Portuguese, compiled inside the executable.
# Use standard LVGL converter (version pinned) rather than relying on OS fonts at boot.
set(PTBR_FONT_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/redeti_font_16.c")
add_custom_command(
  OUTPUT "${PTBR_FONT_SOURCE}"
  COMMAND "${NPM_EXECUTABLE}" exec --yes --package=lv_font_conv@1.5.3 -- lv_font_conv
    --font "${REDETI_FONT_TTF}"
    --range 0x20-0xFF --size 16 --bpp 4 --format lvgl
    --lv-font-name redeti_font_16 --lv-include lvgl/lvgl.h
    --output "${PTBR_FONT_SOURCE}"
  DEPENDS "${REDETI_FONT_TTF}"
  COMMENT "Generating built-in Brazilian Portuguese glyphs using lv_font_conv@1.5.3"
)
add_executable(redeti-ui main.c "${LOGO_SOURCE}" "${PTBR_FONT_SOURCE}")
target_link_libraries(redeti-ui PRIVATE lvgl::lvgl PkgConfig::DRM PkgConfig::JSONC)
target_compile_options(redeti-ui PRIVATE -Wall -Wextra -Werror=implicit-function-declaration)
install(TARGETS redeti-ui RUNTIME DESTINATION bin)
