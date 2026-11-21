#!/bin/sh
# UserPromptSubmit hook: prints unread teamboard messages so they land in Claude's context
# on every prompt. Silent (and never blocks) when the board isn't configured or reachable.
[ -n "$TEAMBOARD_URL" ] && [ -n "$TEAMBOARD_USER" ] || exit 0
curl -s -m 3 -G "${TEAMBOARD_URL%/}/unread" \
  --data-urlencode "user=$TEAMBOARD_USER" \
  -H "Authorization: Bearer $TEAMBOARD_TOKEN" 2>/dev/null || true
exit 0
