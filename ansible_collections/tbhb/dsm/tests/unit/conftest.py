# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

"""A fake ``synowebapi`` for the unit tests.

The replies below are HAND-WRITTEN from the community N4S4/synology-api
wrapper's docstrings and request code. They are NOT recorded from a real NAS,
and Synology publishes no guide for these APIs, so each shape is only as good
as that wrapper. Host names, addresses and accounts are reserved example values.
"""

from __future__ import annotations

import json

import pytest

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.testing import patch_module_args

BINARY = "/usr/syno/bin/synowebapi"

GROUPS_REPLY = {
    "success": True,
    "data": {
        "offset": 0,
        "total": 2,
        "groups": [
            {"gid": 101, "name": "administrators", "description": "System default admin group"},
            {"gid": 100, "name": "users", "description": "System default group"},
        ],
    },
}
USERS_REPLY = {
    "success": True,
    "data": {
        "offset": 0,
        "total": 2,
        "users": [
            {"name": "bob", "uid": 1027, "description": "Bob Example", "email": "bob@example.com", "expired": "normal"},
            {"name": "alice", "uid": 1026, "description": "", "email": "alice@example.com", "expired": "normal"},
        ],
    },
}
MEMBERS = {
    "administrators": {"success": True, "data": {"offset": 0, "total": 1, "users": [{"name": "alice", "uid": 1026}]}},
    "users": {
        "success": True,
        "data": {"offset": 0, "total": 2, "users": [{"name": "bob", "uid": 1027}, {"name": "alice", "uid": 1026}]},
    },
}
SHARES_REPLY = {
    "success": True,
    "data": {
        "total": 2,
        "shares": [
            {"name": "projects", "desc": "Project files", "vol_path": "/volume1", "uuid": "uuid-1", "is_usb_share": False},
            {"name": "archive", "desc": "", "vol_path": "/volume2", "uuid": "uuid-2", "is_usb_share": False},
        ],
    },
}
QUOTA_REPLY = {
    "success": True,
    "data": {
        "user_quota": [
            {
                "volume": "/volume1",
                "quota_status": "normal",
                "deduped": False,
                "support_share_quota": True,
                "shares": [
                    {"name": "projects", "description": "Project files", "quota": 1024},
                    {"name": "archive", "description": "", "quota": 0},
                ],
            }
        ]
    },
}


def permission_reply(items, total=None):
    return {"success": True, "data": {"items": items, "total": len(items) if total is None else total}}


class FakeDsm:
    """Answers ``synowebapi --exec`` calls and records them."""

    def __init__(self):
        self._rules = []
        self.calls = []

    def reply(self, api, method, reply, rc=0, stderr="", **match):
        """Answer calls to ``api``/``method`` whose params include ``match``.

        ``reply`` is a dict (sent as JSON) or a str (sent as is).
        """
        self._rules.append((api, method, match, reply, rc, stderr))

    def run_command(self, args, **kwargs):
        assert isinstance(args, list), "synowebapi must be run with an argument list, not a shell string"
        assert kwargs.get("use_unsafe_shell") is None
        assert args[:2] == [BINARY, "--exec"]
        fields = dict(arg.split("=", 1) for arg in args[2:])
        self.calls.append(fields)
        for api, method, match, reply, rc, stderr in self._rules:
            if fields["api"] == api and fields["method"] == method and all(fields.get(k) == v for k, v in match.items()):
                return rc, reply if isinstance(reply, str) else json.dumps(reply), stderr
        raise AssertionError("no fake reply for %r" % (fields,))

    def calls_to(self, api, method=None):
        return [c for c in self.calls if c["api"] == api and (method is None or c["method"] == method)]


@pytest.fixture
def fake_dsm(monkeypatch):
    fake = FakeDsm()
    monkeypatch.setattr(AnsibleModule, "run_command", lambda self, args, **kw: fake.run_command(args, **kw))
    monkeypatch.setattr(AnsibleModule, "get_bin_path", lambda self, name, **kw: "/usr/syno/bin/%s" % name)
    return fake


@pytest.fixture
def standard_accounts(fake_dsm):
    fake_dsm.reply("SYNO.Core.User", "list", USERS_REPLY)
    fake_dsm.reply("SYNO.Core.Group", "list", GROUPS_REPLY)
    for group, reply in MEMBERS.items():
        fake_dsm.reply("SYNO.Core.Group.Member", "list", reply, group=group)
    return fake_dsm


@pytest.fixture
def run_module(capsys):
    """Run a module's ``main`` and return ``(exit code, result dict)``."""

    def run(main, args=None):
        with patch_module_args(args or {}):
            with pytest.raises(SystemExit) as exit_info:
                main()
        return exit_info.value.code, json.loads(capsys.readouterr().out)

    return run
