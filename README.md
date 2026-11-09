# ansible

Ansible collections for UniFi and Synology DSM, published under the `tbhb` namespace. Each collection is `tbhb.<collection>`, and its modules are `tbhb.<collection>.<module>`.

The modules are tested against fake APIs, so the tests run offline and need no controller or NAS.

## Collections

| Collection | Modules |
| --- | --- |
| `tbhb.dsm` | `user_info`, `group_info`, `share_info`, `share_quota_info` |

`tbhb.dsm` reads Synology DSM state by running `synowebapi --exec` on the NAS. It lives in `ansible_collections/tbhb/dsm/`, because `ansible-test` needs that path. See its README for the options and requirements.

Continuous integration runs `ansible-test sanity` and `ansible-test units` on every pull request.

## License

Apache-2.0. See `LICENSE`.
