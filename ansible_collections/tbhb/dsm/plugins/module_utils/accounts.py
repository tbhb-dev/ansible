# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

"""Group queries that user_info and group_info share.

Source for both calls: the community N4S4/synology-api wrapper, core_group.py
(``get_groups`` and ``get_users``). Synology publishes no guide for them. The
API versions are unverified: the wrapper reads them from the NAS at runtime.
"""

from __future__ import annotations


def list_groups(client):
    """Return the local groups as a list of ``{name, gid, description}`` dicts."""
    data = client.call(
        "SYNO.Core.Group",
        "list",
        version=1,
        params={"type": "local", "offset": 0, "limit": -1, "name_only": False},
    )
    return [
        {"name": g.get("name"), "gid": g.get("gid"), "description": g.get("description", "")}
        for g in data.get("groups", [])
    ]


def list_group_members(client, group):
    """Return the names of the users in one group."""
    data = client.call(
        "SYNO.Core.Group.Member",
        "list",
        version=1,
        params={"group": group, "ingroup": True},
    )
    return [u.get("name") for u in data.get("users", [])]
