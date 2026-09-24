---
summary: Defines channel grouping taxonomy (paid_social, paid_search, email, organic, referral, direct) derived from UTM parameters and referrer data, with subscriber acquisition channel determined by the checkout order that initiated the subscription.
usage_mode: auto
tags:
  - channel attribution
  - UTM parameters
  - acquisition channel
  - subscriber lifecycle
connections:
  - kelder
---

# 0005: Channel grouping from the first order

Date: 2025-06-02 · Status: accepted · Owner: Sanne (data)

Channels are paid_social, paid_search, email, organic, referral and direct, from UTM parameters on
the landing site first and the referrer second. A subscriber's acquisition channel is the channel of
the checkout order that started the subscription.
