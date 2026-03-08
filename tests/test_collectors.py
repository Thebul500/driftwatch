"""Tests for system state collectors."""

from driftwatch import collectors


class TestRunHelper:
    """Tests for the _run helper."""

    def test_run_valid_command(self):
        result = collectors._run(["echo", "hello"])
        assert result == "hello"

    def test_run_invalid_command(self):
        result = collectors._run(["nonexistent_command_xyz"])
        assert result == ""

    def test_run_timeout(self):
        # A very short timeout on a command that would take longer
        result = collectors._run(["sleep", "10"], timeout=1)
        assert result == ""


class TestCollectDocker:
    """Tests for Docker container collection."""

    def test_returns_dict(self):
        result = collectors.collect_docker()
        assert isinstance(result, dict)

    def test_containers_have_expected_keys(self):
        result = collectors.collect_docker()
        # If Docker is running and has containers, check structure
        for name, info in result.items():
            assert isinstance(name, str)
            assert isinstance(info, dict)
            assert "id" in info
            assert "image" in info


class TestCollectCrontabs:
    """Tests for crontab collection."""

    def test_returns_dict(self):
        result = collectors.collect_crontabs()
        assert isinstance(result, dict)

    def test_values_are_lists_of_strings(self):
        result = collectors.collect_crontabs()
        for key, entries in result.items():
            assert isinstance(key, str)
            assert isinstance(entries, list)
            for entry in entries:
                assert isinstance(entry, str)


class TestCollectPackages:
    """Tests for package collection."""

    def test_returns_dict(self):
        result = collectors.collect_packages()
        assert isinstance(result, dict)

    def test_has_packages(self):
        """On a real Linux system, there should be installed packages."""
        result = collectors.collect_packages()
        # This machine is Ubuntu, so dpkg should find packages
        assert len(result) > 0

    def test_values_are_version_strings(self):
        result = collectors.collect_packages()
        for pkg, version in result.items():
            assert isinstance(pkg, str)
            assert isinstance(version, str)
            assert len(version) > 0


class TestCollectSystemd:
    """Tests for systemd service collection."""

    def test_returns_dict(self):
        result = collectors.collect_systemd()
        assert isinstance(result, dict)

    def test_services_have_expected_keys(self):
        result = collectors.collect_systemd()
        for name, info in result.items():
            assert isinstance(name, str)
            assert isinstance(info, dict)
            assert "active" in info
            assert "sub" in info


class TestCollectAll:
    """Tests for the combined collector."""

    def test_returns_all_sections(self):
        result = collectors.collect_all()
        assert isinstance(result, dict)
        assert "docker" in result
        assert "crontabs" in result
        assert "packages" in result
        assert "systemd" in result

    def test_each_section_is_dict(self):
        result = collectors.collect_all()
        for section, data in result.items():
            assert isinstance(data, dict), f"{section} should be a dict"
