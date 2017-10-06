#!/bin/sh

TMPFILE=`mktemp`
NODE='node'

if [ -x /usr/bin/nodejs ]; then
    NODE='/usr/bin/nodejs'
fi
"$NODE" nest_get_token.js | tee "$TMPFILE"

TOKEN=`cat "$TMPFILE"  | grep 'token=' | sed 's/.*token=//'`

"$NODE" nest_get_snapshoturl_by_token.js "$TOKEN"
