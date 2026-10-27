"""Review native appliance boot recipe without touching any attached disk."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ApplianceBuildSafetyTests(unittest.TestCase):
    def test_recipe_disables_graphical_desktop(self):
        cfg = (ROOT / "appliance/boot/900-redeti-appliance.yaml").read_text()
        self.assertIn("dostartx: false", cfg)
        self.assertIn("loadsrm: true", cfg)
        self.assertIn("autorun:", cfg)
        self.assertIn("/opt/redeti-appliance/launch.sh", cfg)
        self.assertNotIn("gui_autostart", cfg)

    def test_appliance_does_not_use_legacy_web(self):
        iso = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        self.assertNotIn("boot_gui", iso)
        self.assertNotIn("firefox", launch.lower())
        self.assertNotIn("startx", launch.lower())
        self.assertNotIn("http://", launch)
        self.assertIn("redeti-ui", iso + launch)

    def test_compiler_does_not_mount_host_disks(self):
        native = (ROOT / "appliance/build/build-native-arch.sh").read_text()
        self.assertIn(":/project:ro", native)
        self.assertNotIn("--privileged", native)
        self.assertNotIn("/dev/sd", native)
        self.assertNotIn("dd if=", native)

    def test_build_preserves_older_iso_until_qemu_approval(self):
        script = (ROOT / "appliance/build/build-local.sh").read_text()
        self.assertIn("sha256sum", script)
        self.assertNotIn("prune-recovery-isos.sh", script)

    def test_arch_builder_emits_portable_checksum(self):
        script = (ROOT / "appliance/build/build-native-arch.sh").read_text()
        self.assertIn("(cd /out && sha256sum redeti-ui > redeti-ui.sha256)", script)
        self.assertNotIn("sha256sum /out/redeti-ui > /out/redeti-ui.sha256", script)

    def test_appliance_builder_accepts_old_docker_checksum_path(self):
        script = (ROOT / "appliance/build/build-local.sh").read_text()
        self.assertIn('stored="$(awk', script)
        self.assertIn('computed="$(sha256sum -- "$ui"', script)
        self.assertIn("Native ELF checksum mismatch", script)
        self.assertNotIn('sha256sum -c "$(basename -- "$ui").sha256"', script)

    def test_iso_requires_current_native_source_commit(self):
        native = (ROOT / "appliance/build/build-native-arch.sh").read_text()
        iso = (ROOT / "appliance/build/build-local.sh").read_text()
        self.assertIn('source_head="$(git -C "$repo" rev-parse --verify HEAD)"', native)
        self.assertIn('"$work/out/redeti-ui.commit"', native)
        self.assertIn('git -C "$repo" diff --quiet', native)
        self.assertIn('source_commit="$(tr -d', iso)
        self.assertIn('"$source_commit" = "$current_commit"', iso)
        self.assertIn("Stale native ELF", iso)
        self.assertIn('git -C "$root" diff --quiet', iso)

    def test_iso_filename_and_manifest_identify_source_revision(self):
        script=(ROOT/"appliance/build/build-local.sh").read_text()
        self.assertIn('revision="${current_commit:0:8}"',script)
        self.assertIn('RedeTI-Recovery-OS-appliance-$revision-$stamp.iso',script)
        self.assertIn('printf \'source_commit=%s',script)
        self.assertIn('printf \'iso_sha256=%s',script)
        self.assertIn('> "$iso.buildinfo"',script)
        self.assertIn('Source revision: $current_commit',script)
        self.assertIn('Windows/QEMU copy',script)

    def test_source_revision_is_injected_into_hermes_and_ci_builds(self):
        native=(ROOT/"appliance/build/build-native-arch.sh").read_text()
        cmake=(ROOT/"appliance/native/CMakeLists.txt").read_text()
        ci=(ROOT/".github/workflows/native-appliance.yml").read_text()
        self.assertIn('-e REDETI_SOURCE_COMMIT="$source_head"',native)
        self.assertIn('-DREDETI_SOURCE_COMMIT="$REDETI_SOURCE_COMMIT"',native)
        self.assertIn('strings /out/redeti-ui | grep -Fx "$source_rev_short" >/dev/null',native)
        self.assertIn('-DREDETI_SOURCE_COMMIT="$GITHUB_SHA"',ci)
        self.assertIn('if(DEFINED REDETI_SOURCE_COMMIT',cmake)
        self.assertIn('string(SUBSTRING "${REDETI_SOURCE_REV}" 0 8 REDETI_BUILD_REV)',cmake)
        self.assertIn('message(FATAL_ERROR "Unable to resolve recovery UI source commit")',cmake)
        self.assertNotIn('set(REDETI_BUILD_REV "unknown")',cmake)

    def test_display_version_matches_iso_and_native_build_metadata(self):
        native=(ROOT/"appliance/build/build-native-arch.sh").read_text()
        iso=(ROOT/"appliance/build/build-local.sh").read_text()
        cmake=(ROOT/"appliance/native/CMakeLists.txt").read_text()
        ui=(ROOT/"appliance/native/ui/dashboard.c").read_text()
        self.assertIn('redeti-build-id.txt',cmake)
        self.assertIn('app_version=v${PROJECT_VERSION}',cmake)
        self.assertIn('build_tag=${REDETI_BUILD_TAG}',cmake)
        self.assertIn('install -m 0644 /cache/lvgl/redeti-build-id.txt /out/redeti-ui.buildinfo',native)
        self.assertIn('strings /out/redeti-ui | grep -Fx "$build_tag"',native)
        self.assertIn('grep -Fx "source_commit=$current_commit" "$ui.buildinfo"',iso)
        self.assertIn("printf 'app_version=%s",iso)
        self.assertIn("printf 'build_tag=%s",iso)
        for name in ('REDETI_APP_VERSION','REDETI_BUILD_TAG','REDETI_BUILD_REV'):
            self.assertIn(f'txt(ver,{name},',ui)

    def test_boot_logs_native_crash_without_silent_console(self):
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        self.assertIn("/run/redeti/ui.log", launch)
        self.assertIn("/run/redeti/ui.exit", launch)
        self.assertIn("Falha na interface nativa", launch)
        self.assertIn("tail -n 35", launch)

    def test_early_splash_is_first_userspace_service_with_fallback(self):
        compose = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        launch = (ROOT / "appliance/boot/launch.sh").read_text()
        unit = (ROOT / "appliance/boot/redeti-early-splash.service").read_text()
        self.assertIn("sysinit.target.wants", compose)
        self.assertIn("redeti-early-splash.service", compose)
        self.assertIn("DefaultDependencies=no", unit)
        self.assertIn("Before=sysinit.target", unit)
        self.assertIn("ConditionPathExists=/dev/fb0", unit)
        self.assertIn("systemctl is-active --quiet redeti-early-splash.service", launch)
        self.assertIn("systemctl stop redeti-early-splash.service", launch)

    def test_initramfs_is_not_modified_for_python_splash(self):
        compose = (ROOT / "appliance/build/compose-appliance.sh").read_text()
        self.assertNotIn("build_into_initramfs", compose)
        self.assertNotIn("mkinitcpio", compose.lower())

    def test_shell_scripts_have_valid_syntax(self):
        for name in ("appliance/build/build-native-arch.sh", "appliance/build/compose-appliance.sh",
                     "appliance/build/build-local.sh", "appliance/boot/launch.sh"):
            process = subprocess.run(["bash", "-n", str(ROOT / name)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, f"{name}: {process.stderr}")


if __name__ == "__main__":
    unittest.main()
