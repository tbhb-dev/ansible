# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

"""Client for DSM's ``synowebapi --exec`` command, run on the managed node.

Synology publishes no guide for the SYNO.Core.* APIs. The request and reply
shapes used here come from the community ``N4S4/synology-api`` wrapper and
are cited in each module; anything not confirmed there is marked unverified.
"""

from __future__ import annotations

import json
import re

DEFAULT_BINARY = "synowebapi"
# DSM keeps its command line tools here, which a non-login shell may not have
# on PATH.
BINARY_SEARCH_DIRS = ["/usr/syno/bin", "/usr/syno/sbin"]

_API_RE = re.compile(r"\ASYNO(\.[A-Za-z0-9_]+)+\Z")
_METHOD_RE = re.compile(r"\A[A-Za-z0-9_]+\Z")
_KEY_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")
_RESERVED_KEYS = frozenset({"api", "method", "version"})
_MAX_VALUE_LENGTH = 4096


class SynoWebApiError(Exception):
    """Base class for every error the client raises."""


class SynoWebApiUsageError(SynoWebApiError):
    """A request was refused before anything ran, because a value failed validation."""


class SynoWebApiExecError(SynoWebApiError):
    """``synowebapi`` could not be found, or it exited non-zero."""

    def __init__(self, message, rc=None, stderr=""):
        super().__init__(message)
        self.rc = rc
        self.stderr = stderr


class SynoWebApiResponseError(SynoWebApiError):
    """The reply was not the JSON object the client expects."""

    def __init__(self, message, output=""):
        super().__init__(message)
        self.output = output


class SynoWebApiApiError(SynoWebApiError):
    """DSM answered with ``success: false``; ``code`` is DSM's ``error.code``."""

    def __init__(self, api, method, code):
        super().__init__("DSM error %s from %s %s" % (code, api, method))
        self.api = api
        self.method = method
        self.code = code


def _render_value(key, value):
    """Return the text of one ``key=value`` parameter, or raise on a bad value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, dict)):
        # Compound values travel as compact JSON, which is how DSM takes them.
        text = json.dumps(value, separators=(",", ":"), ensure_ascii=True)
    elif isinstance(value, str):
        text = value
    else:
        raise SynoWebApiUsageError("parameter %r has an unsupported type %s" % (key, type(value).__name__))
    if len(text) > _MAX_VALUE_LENGTH:
        raise SynoWebApiUsageError("parameter %r is longer than %d characters" % (key, _MAX_VALUE_LENGTH))
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in text):
        raise SynoWebApiUsageError("parameter %r contains a control character" % key)
    return text


def build_command(binary, api, method, version, params=None):
    """Build the argument list for one call. Nothing here goes near a shell."""
    if not isinstance(api, str) or not _API_RE.match(api):
        raise SynoWebApiUsageError("invalid API name %r" % (api,))
    if not isinstance(method, str) or not _METHOD_RE.match(method):
        raise SynoWebApiUsageError("invalid method name %r" % (method,))
    if isinstance(version, bool) or not isinstance(version, int) or not 1 <= version <= 99:
        raise SynoWebApiUsageError("invalid API version %r" % (version,))

    args = [binary, "--exec", "api=%s" % api, "method=%s" % method, "version=%d" % version]
    for key, value in (params or {}).items():
        if not isinstance(key, str) or not _KEY_RE.match(key) or key in _RESERVED_KEYS:
            raise SynoWebApiUsageError("invalid parameter name %r" % (key,))
        args.append("%s=%s" % (key, _render_value(key, value)))
    return args


def parse_reply(api, method, output):
    """Parse a reply and return its ``data``, or raise the matching error."""
    try:
        reply = json.loads(output)
    except ValueError as exc:
        raise SynoWebApiResponseError("reply from %s %s is not valid JSON: %s" % (api, method, exc), output)
    if not isinstance(reply, dict) or not isinstance(reply.get("success"), bool):
        raise SynoWebApiResponseError("reply from %s %s has no boolean 'success'" % (api, method), output)

    if not reply["success"]:
        error = reply.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        if isinstance(code, bool) or not isinstance(code, int):
            raise SynoWebApiResponseError(
                "failed reply from %s %s has no integer error.code" % (api, method), output
            )
        raise SynoWebApiApiError(api, method, code)

    data = reply.get("data", {})
    if not isinstance(data, dict):
        raise SynoWebApiResponseError("'data' in the reply from %s %s is not an object" % (api, method), output)
    return data


class SynoWebApi:
    """Runs ``synowebapi --exec`` through an AnsibleModule."""

    def __init__(self, module, binary=DEFAULT_BINARY):
        self._module = module
        self._binary = binary

    def _binary_path(self):
        path = self._module.get_bin_path(self._binary, opt_dirs=BINARY_SEARCH_DIRS)
        if not path:
            raise SynoWebApiExecError("%s was not found on the managed node" % self._binary)
        return path

    def call(self, api, method, version=1, params=None):
        """Run one API call and return the reply's ``data`` object."""
        args = build_command(self._binary_path(), api, method, version, params)
        # An argument list makes run_command exec the binary directly, with no shell.
        rc, stdout, stderr = self._module.run_command(args, check_rc=False)
        if rc != 0:
            raise SynoWebApiExecError(
                "synowebapi exited with status %s for %s %s" % (rc, api, method), rc=rc, stderr=stderr
            )
        return parse_reply(api, method, stdout)


def fail_json_from_error(module, exc):
    """Fail the module with a message, plus the DSM error code when there is one."""
    details = {}
    if isinstance(exc, SynoWebApiApiError):
        details["dsm_error_code"] = exc.code
    elif isinstance(exc, SynoWebApiExecError):
        details["rc"] = exc.rc
        details["stderr"] = exc.stderr
    elif isinstance(exc, SynoWebApiResponseError):
        details["output"] = exc.output
    module.fail_json(msg=str(exc), **details)
