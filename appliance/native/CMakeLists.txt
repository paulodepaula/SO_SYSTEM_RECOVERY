cmake_minimum_required(VERSION 3.20)
project(redeti_recovery_appliance VERSION 0.5 LANGUAGES C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
include(FetchContent)
find_package(PkgConfig REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
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
# The verified Montserrat built-in font avoids LVGL 8/9 generated font ABI mismatch.
# The UI transliterates accented strings until a visually tested LVGL 9 font exists.
add_executable(redeti-ui main.c input.c ui/dashboard.c "${LOGO_SOURCE}")
target_link_libraries(redeti-ui PRIVATE lvgl::lvgl PkgConfig::DRM PkgConfig::JSONC)
target_compile_options(redeti-ui PRIVATE -Wall -Wextra -Werror=implicit-function-declaration)
install(TARGETS redeti-ui RUNTIME DESTINATION bin)

# CTest draws the real MVP using an in-memory display, without DRM, disks or network.
include(CTest)
if(BUILD_TESTING)
  add_executable(redeti-ui-render-smoke
    tests/render_smoke.c input.c ui/dashboard.c "${LOGO_SOURCE}")
  target_link_libraries(redeti-ui-render-smoke PRIVATE lvgl::lvgl PkgConfig::DRM PkgConfig::JSONC)
  add_test(NAME render-mvp-1280x720 COMMAND redeti-ui-render-smoke 1280 720)
  add_test(NAME render-mvp-1589x990 COMMAND redeti-ui-render-smoke 1589 990)
  set_tests_properties(render-mvp-1280x720 render-mvp-1589x990 PROPERTIES TIMEOUT 15)
endif()
