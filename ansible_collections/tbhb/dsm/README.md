# tbhb.dsm

Ansible modules for Synology DSM. They run DSM's `synowebapi --exec` on the managed node, over the SSH connection Ansible already has, and read the reply.

## Modules

| Module | Reads |
| --- | --- |
| `tbhb.dsm.user_info` | Local users, with their groups |
| `tbhb.dsm.group_info` | Local groups, with their members |
| `tbhb.dsm.share_info` | Shared folders, with the access of named users and groups |
| `tbhb.dsm.share_quota_info` | The quota of a user or group on each share |

Every module is read-only and supports check mode. Each documents its options, examples and return values: run `ansible-doc tbhb.dsm.<module>`.

## Requirements

- ansible-core 2.21 or later.
- A managed node that has `/usr/syno/bin/synowebapi`, reached as a user who may run it. On DSM that is root, so set `become: true`.

## Sources of the API shapes

Synology publishes no guide for the `SYNO.Core.*` APIs the modules call. Their request and reply shapes come from the community [N4S4/synology-api](https://github.com/N4S4/synology-api) wrapper. Each module's source cites the exact calls and marks what is unverified. The unit tests use replies written by hand from that wrapper, not replies recorded from a NAS.

## Development

`ansible-test` only works from inside `ansible_collections/<namespace>/<name>/`, so run it from this directory:

```sh
ansible-test sanity --venv --requirements --python 3.13
ansible-test units --venv --requirements --python 3.13
```

The modules are licensed under Apache-2.0, not GPLv3, so `tests/sanity/ignore-2.21.txt` ignores the `validate-modules:missing-gplv3-license` check for them.
