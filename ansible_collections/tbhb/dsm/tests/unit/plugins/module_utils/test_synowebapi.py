# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

import pytest

from ansible_collections.tbhb.dsm.plugins.module_utils import synowebapi as sw
from ansible_collections.tbhb.dsm.plugins.module_utils.synowebapi import (
    SynoWebApi,
    SynoWebApiApiError,
    SynoWebApiExecError,
    SynoWebApiResponseError,
    SynoWebApiUsageError,
    build_command,
    parse_reply,
)


class FakeModule:
    def __init__(self, rc=0, stdout="", stderr="", path="/usr/syno/bin/synowebapi"):
        self.result = (rc, stdout, stderr)
        self.path = path
        self.run_args = None

    def get_bin_path(self, name, opt_dirs=None):
        self.opt_dirs = opt_dirs
        return self.path

    def run_command(self, args, **kwargs):
        self.run_args = args
        self.run_kwargs = kwargs
        return self.result


class TestBuildCommand:
    def test_argument_list(self):
        args = build_command("/bin/synowebapi", "SYNO.Core.User", "list", 1, {"type": "local", "limit": -1})
        assert args == [
            "/bin/synowebapi",
            "--exec",
            "api=SYNO.Core.User",
            "method=list",
            "version=1",
            "type=local",
            "limit=-1",
        ]

    def test_value_types(self):
        args = build_command("b", "SYNO.Core.User", "list", 1, {"a": True, "b": False, "c": ["x", "y"], "d": {"k": 1}})
        assert args[5:] == ["a=true", "b=false", 'c=["x","y"]', 'd={"k":1}']

    def test_shell_metacharacters_in_a_value_stay_one_argument(self):
        value = "x; rm -rf / $(id) `id` | & > /tmp/f"
        args = build_command("b", "SYNO.Core.User", "get", 1, {"name": value})
        assert args[-1] == "name=" + value

    @pytest.mark.parametrize(
        "api", ["", "SYNO", "syno.Core.User", "SYNO.Core.User; id", "SYNO.Core User", "SYNO..Core", "SYNO.Core.User\n", None]
    )
    def test_bad_api(self, api):
        with pytest.raises(SynoWebApiUsageError):
            build_command("b", api, "list", 1)

    @pytest.mark.parametrize("method", ["", "list;id", "li st", "list\n", "-x", None])
    def test_bad_method(self, method):
        with pytest.raises(SynoWebApiUsageError):
            build_command("b", "SYNO.Core.User", method, 1)

    @pytest.mark.parametrize("version", [0, 100, -1, "1", 1.0, True, None])
    def test_bad_version(self, version):
        with pytest.raises(SynoWebApiUsageError):
            build_command("b", "SYNO.Core.User", "list", version)

    @pytest.mark.parametrize("key", ["", "1a", "a b", "a=b", "--exec", "a;b", "api", "method", "version", 1, None])
    def test_bad_parameter_name(self, key):
        with pytest.raises(SynoWebApiUsageError):
            build_command("b", "SYNO.Core.User", "list", 1, {key: "v"})

    @pytest.mark.parametrize("value", ["a\nb", "a\x00b", "a\rb", "a\x7fb", "x" * 5000, 1.5, None, b"x", object()])
    def test_bad_parameter_value(self, value):
        with pytest.raises(SynoWebApiUsageError):
            build_command("b", "SYNO.Core.User", "list", 1, {"name": value})

    def test_control_character_nested_in_json_is_escaped_not_rejected(self):
        # json.dumps escapes the newline, so the argument itself holds none.
        args = build_command("b", "SYNO.Core.User", "list", 1, {"names": ["a\nb"]})
        assert args[-1] == 'names=["a\\nb"]'


class TestParseReply:
    def test_success_returns_data(self):
        assert parse_reply("A", "m", '{"success": true, "data": {"x": 1}}\n') == {"x": 1}

    def test_success_without_data_is_empty(self):
        assert parse_reply("A", "m", '{"success": true}') == {}

    def test_dsm_error_code(self):
        with pytest.raises(SynoWebApiApiError) as exc_info:
            parse_reply("SYNO.Core.User", "list", '{"success": false, "error": {"code": 119}}')
        assert exc_info.value.code == 119
        assert exc_info.value.api == "SYNO.Core.User"
        assert "119" in str(exc_info.value)

    @pytest.mark.parametrize(
        "output",
        [
            "",
            "not json",
            '{"success": true',
            "[]",
            '"text"',
            "null",
            "{}",
            '{"success": "true"}',
            '{"success": 1}',
            '{"success": true, "data": []}',
            '{"success": false}',
            '{"success": false, "error": "boom"}',
            '{"success": false, "error": {}}',
            '{"success": false, "error": {"code": "119"}}',
            '{"success": false, "error": {"code": true}}',
        ],
    )
    def test_malformed(self, output):
        with pytest.raises(SynoWebApiResponseError) as exc_info:
            parse_reply("A", "m", output)
        assert exc_info.value.output == output


class TestClient:
    def test_call_runs_an_argument_list_without_a_shell(self):
        module = FakeModule(stdout='{"success": true, "data": {"ok": 1}}')
        assert SynoWebApi(module).call("SYNO.Core.User", "list", 1, {"type": "local"}) == {"ok": 1}
        assert isinstance(module.run_args, list)
        assert module.run_args[0] == "/usr/syno/bin/synowebapi"
        assert not module.run_kwargs.get("use_unsafe_shell")
        assert module.run_kwargs["check_rc"] is False
        assert module.opt_dirs == sw.BINARY_SEARCH_DIRS

    def test_binary_missing(self):
        with pytest.raises(SynoWebApiExecError, match="not found"):
            SynoWebApi(FakeModule(path=None)).call("SYNO.Core.User", "list")

    def test_nonzero_exit(self):
        module = FakeModule(rc=127, stderr="boom")
        with pytest.raises(SynoWebApiExecError) as exc_info:
            SynoWebApi(module).call("SYNO.Core.User", "list")
        assert exc_info.value.rc == 127
        assert exc_info.value.stderr == "boom"

    def test_invalid_request_never_runs_anything(self):
        module = FakeModule(stdout='{"success": true}')
        with pytest.raises(SynoWebApiUsageError):
            SynoWebApi(module).call("SYNO.Core.User", "list; id")
        assert module.run_args is None

    def test_dsm_error(self):
        module = FakeModule(stdout='{"success": false, "error": {"code": 105}}')
        with pytest.raises(SynoWebApiApiError) as exc_info:
            SynoWebApi(module).call("SYNO.Core.User", "list")
        assert exc_info.value.code == 105
