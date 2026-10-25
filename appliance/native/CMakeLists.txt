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

# Hermes supplies the trusted host Git SHA explicitly, because a read-only
# bind mount may fail git safe.directory checks inside the Arch container.
# CI supplies GITHUB_SHA. Never ship an ambiguous 'unknown' revision.
if(DEFINED REDETI_SOURCE_COMMIT AND NOT REDETI_SOURCE_COMMIT STREQUAL "")
  set(REDETI_SOURCE_REV "${REDETI_SOURCE_COMMIT}")
else()
  execute_process(
    COMMAND git rev-parse HEAD
    WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/../.."
    OUTPUT_VARIABLE REDETI_SOURCE_REV
    RESULT_VARIABLE REDETI_GIT_STATUS
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
  if(NOT REDETI_GIT_STATUS EQUAL 0)
    message(FATAL_ERROR "Unable to resolve recovery UI source commit")
  endif()
endif()
string(LENGTH "${REDETI_SOURCE_REV}" REDETI_SOURCE_REV_LENGTH)
if(NOT REDETI_SOURCE_REV MATCHES "^[0-9a-fA-F]+$" OR
   NOT REDETI_SOURCE_REV_LENGTH EQUAL 40)
  message(FATAL_ERROR "Recovery UI source revision must be a complete 40-character Git SHA")
endif()
string(SUBSTRING "${REDETI_SOURCE_REV}" 0 8 REDETI_BUILD_REV)
message(STATUS "RedeTI Recovery OS source revision: ${REDETI_SOURCE_REV}")

set(LOGO_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/logo_pd.c")
add_custom_command(
  OUTPUT "${LOGO_SOURCE}"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/generate_logo.py"
    "${CMAKE_CURRENT_LIST_DIR}/../../assets/logo-paulo.svg" "${LOGO_SOURCE}"
  DEPENDS "${CMAKE_CURRENT_LIST_DIR}/generate_logo.py"
          "${CMAKE_CURRENT_LIST_DIR}/../../assets/logo-paulo.svg"
  COMMENT "Converting original PD logo to native LVGL RGB565"
)
# Offline generated original art: no filesystem or third-party UI assets at runtime.
set(PREMIUM_SOURCE "${CMAKE_CURRENT_BINARY_DIR}/premium_assets.c")
add_custom_command(
  OUTPUT "${PREMIUM_SOURCE}"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/premium_assets.py" "${PREMIUM_SOURCE}"
  DEPENDS "${CMAKE_CURRENT_LIST_DIR}/premium_assets.py"
          "${CMAKE_CURRENT_LIST_DIR}/assets/source/hero-laptop-panel.png"
  COMMENT "Embedding supplied notebook and generating LVGL icon rasters"
)
# The verified Montserrat built-in font avoids LVGL 8/9 generated font ABI mismatch.
# The UI transliterates accented strings until a visually tested LVGL 9 font exists.
add_executable(redeti-ui main.c input.c ui/dashboard.c ui/theme.c "${LOGO_SOURCE}" "${PREMIUM_SOURCE}")
target_link_libraries(redeti-ui PRIVATE lvgl::lvgl PkgConfig::DRM PkgConfig::JSONC)
target_compile_definitions(redeti-ui PRIVATE REDETI_BUILD_REV="${REDETI_BUILD_REV}")
target_compile_options(redeti-ui PRIVATE -Wall -Wextra -Werror=implicit-function-declaration)
install(TARGETS redeti-ui RUNTIME DESTINATION bin)

# CTest draws the real MVP using an in-memory display, without DRM, disks or network.
include(CTest)
if(BUILD_TESTING)
  add_executable(redeti-ui-render-smoke
    tests/render_smoke.c input.c ui/dashboard.c ui/theme.c "${LOGO_SOURCE}" "${PREMIUM_SOURCE}")
  target_link_libraries(redeti-ui-render-smoke PRIVATE lvgl::lvgl PkgConfig::DRM PkgConfig::JSONC)
  target_compile_definitions(redeti-ui-render-smoke PRIVATE REDETI_BUILD_REV="${REDETI_BUILD_REV}")
  add_test(NAME render-mvp-1280x720 COMMAND redeti-ui-render-smoke 1280 720)
  add_test(NAME render-mvp-1366x768 COMMAND redeti-ui-render-smoke 1366 768)
  add_test(NAME render-mvp-1589x990 COMMAND redeti-ui-render-smoke 1589 990)
  set_tests_properties(render-mvp-1280x720 render-mvp-1366x768 render-mvp-1589x990 PROPERTIES TIMEOUT 25)
endif()
