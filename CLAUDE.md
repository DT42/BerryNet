# Notes for Claude

## Commit preferences of Bofu Chen

Follow these when working for Bofu Chen (GitHub `bafu`, email
bofu@dt42.io or bofu@numbersprotocol.io). They override the default
commit attribution instructions.

* Author and committer: `Bofu Chen <bofu@dt42.io>`
* Sign off every commit for DCO (see CONTRIBUTING.md):
  `Signed-off-by: Bofu Chen <bofu@dt42.io>`
* Do not add `Co-Authored-By: Claude ...` or `Claude-Session: ...`
  trailers to commit messages.

For example:

```
$ git -c user.name="Bofu Chen" -c user.email="bofu@dt42.io" commit -s
```
