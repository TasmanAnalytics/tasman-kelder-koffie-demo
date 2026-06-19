# 0008: Legacy pause restores are continuations

Date: 2026-03-17 · Status: accepted · Owner: Sanne (data)

Operations re-creates subscriptions whose pause the 12 March migration wiped (decision 0007) as new
Recharge subscriptions, marked `restore_source = legacy_pause`. A restore continues the original
subscription: same key, same tenure. It is not a new subscriber and not acquisition. See
`quirks/legacy_pause_restores.md`.
