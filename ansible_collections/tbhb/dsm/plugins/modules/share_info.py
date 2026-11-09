#!/usr/bin/python
# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

from __future__ import annotations

DOCUMENTATION = r"""
module: share_info
short_description: Read the shared folders of a Synology DSM NAS
version_added: "0.1.0"
description:
  - Lists the shared folders on a DSM NAS, and the access that named users and groups have to each, by running C(synowebapi --exec) on the managed node.
  - Read-only. It changes nothing on the NAS.
  - Needs a user that may run C(synowebapi), which on DSM is root. Use C(become).
  - Synology publishes no guide for these APIs. See the module source for the references and for what is unverified.
options:
  name:
    description:
      - Return only the shares with these names.
      - A name that matches no share is left out of the result and is not an error.
    type: list
    elements: str
    required: false
  users:
    description:
      - Local users whose access to each returned share is read.
      - Without O(users) and O(groups) the module makes no permission calls.
    type: list
    elements: str
    required: false
  groups:
    description:
      - Local groups whose access to each returned share is read.
    type: list
    elements: str
    required: false
attributes:
  check_mode:
    support: full
    description: The module only reads, so it runs the same way in check mode.
  diff_mode:
    support: none
    description: The module changes nothing, so there is no diff.
author:
  - Tony Burns (@tbhb)
"""

EXAMPLES = r"""
- name: Read every share
  tbhb.dsm.share_info:
  become: true
  register: shares

- name: Read what alice and the users group may do on one share
  tbhb.dsm.share_info:
    name: projects
    users:
      - alice
    groups:
      - users
  become: true
  register: projects
"""

RETURN = r"""
shares:
  description: The shared folders, sorted by name.
  returned: success
  type: list
  elements: dict
  contains:
    name:
      description: The share name.
      type: str
      sample: projects
    description:
      description: The share description.
      type: str
      sample: Project files
    volume_path:
      description: The volume the share lives on.
      type: str
      sample: /volume1
    uuid:
      description: DSM's identifier for the share.
      type: str
      sample: 00000000-0000-4000-8000-000000000000
    permissions:
      description:
        - Access of the named users and groups, as V(users) and V(groups) dicts that map a name to its access.
        - A name that DSM returns no entry for is left out.
      type: dict
      contains:
        users:
          description: Access by user name.
          type: dict
          sample: {"alice": "read_write"}
        groups:
          description: Access by group name.
          type: dict
          sample: {"users": "read_only"}
"""

# API references. Synology publishes no guide for SYNO.Core.*. Both are cited to
# the community wrapper N4S4/synology-api, synology_api/core_share.py:
#   SYNO.Core.Share             method=list  shareType=all
#       (list_folders)  cited; version unverified (the wrapper reads it at runtime)
#   SYNO.Core.Share.Permission  method=list  action=enum  user_group_type=
#       local_user | local_group  (get_folder_permissions)
#       cited; version unverified. The reply's items carry is_deny, is_readonly
#       and is_writable, which map to deny, read_only and read_write.
# Unverified: whether limit/offset paging behaves as assumed when limit is 100.

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.tbhb.dsm.plugins.module_utils.synowebapi import (
    SynoWebApi,
    SynoWebApiError,
    SynoWebApiResponseError,
    fail_json_from_error,
)

PAGE_SIZE = 100
# Pages are fetched until the reported total is reached. This bound stops a NAS
# that keeps returning items from looping the module forever.
MAX_PAGES = 100


def access_of(item):
    if item.get("is_deny"):
        return "deny"
    if item.get("is_writable"):
        return "read_write"
    if item.get("is_readonly"):
        return "read_only"
    return "none"


def read_access(client, share, group_type, names):
    """Return ``{name: access}`` for the wanted names on one share."""
    found = {}
    offset = 0
    for page in range(MAX_PAGES):
        data = client.call(
            "SYNO.Core.Share.Permission",
            "list",
            version=1,
            params={
                "name": share,
                "action": "enum",
                "user_group_type": group_type,
                "offset": offset,
                "limit": PAGE_SIZE,
                "is_unite_permission": False,
                "with_inherit": False,
            },
        )
        items = data.get("items", [])
        for item in items:
            if item.get("name") in names:
                found[item["name"]] = access_of(item)
        offset += len(items)
        total = data.get("total", 0)
        if not items or offset >= total:
            return found
    raise SynoWebApiResponseError("permissions of share %s did not end after %d pages" % (share, MAX_PAGES))


def main():
    module = AnsibleModule(
        argument_spec={
            "name": {"type": "list", "elements": "str"},
            "users": {"type": "list", "elements": "str"},
            "groups": {"type": "list", "elements": "str"},
        },
        supports_check_mode=True,
    )
    wanted = module.params["name"]
    users = module.params["users"]
    groups = module.params["groups"]
    client = SynoWebApi(module)

    shares = []
    try:
        data = client.call("SYNO.Core.Share", "list", version=1, params={"shareType": "all"})
        for entry in data.get("shares", []):
            name = entry.get("name")
            if wanted is not None and name not in wanted:
                continue
            share = {
                "name": name,
                "description": entry.get("desc", ""),
                "volume_path": entry.get("vol_path"),
                "uuid": entry.get("uuid"),
                "permissions": {},
            }
            if users:
                share["permissions"]["users"] = read_access(client, name, "local_user", set(users))
            if groups:
                share["permissions"]["groups"] = read_access(client, name, "local_group", set(groups))
            shares.append(share)
    except SynoWebApiError as exc:
        fail_json_from_error(module, exc)
    module.exit_json(changed=False, shares=sorted(shares, key=lambda s: s["name"]))


if __name__ == "__main__":
    main()
