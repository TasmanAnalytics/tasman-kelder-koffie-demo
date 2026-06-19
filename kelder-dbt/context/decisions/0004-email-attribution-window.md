# 0004: Email attribution window is five days after a click

Date: 2025-03-04 · Status: accepted · Owner: Sanne (data), agreed with Joris (retention)

An order is email-attributed if the same Klaviyo profile clicked an email in the five days before
it. Opens do not count. We compute this ourselves from Klaviyo events rather than using Klaviyo's
attributed_message_id, so the rule is visible in SQL.
