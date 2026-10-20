---
tags: [paper, curated]
relevance: 3
read: 2026-10-19
---
# The Pre-FOMC Announcement Drift
★★★☆☆  ·  Must-read (curated)  ·  [source](https://papers.ssrn.com/sol3/Delivery.cfm?abstractid=1923197)

## What Volta learned
The Pre-FOMC Announcement Drift refers to the observed phenomenon where the stock market tends to drift upward before a Federal Open Market Committee (FOMC) announcement. This drift is often attributed to the market's anticipation and positioning ahead of the announcement.

## Why it matters (or not)
This is a well-known paper discussing a specific market anomaly related to FOMC announcements, which can be relevant for traders but does not provide direct insights into volatility models or risk management.

## Concepts
[[FOMC]], announcement drift, market anticipation

## Idea
Investigate if the Pre-FOMC Announcement Drift can be predicted or enhanced using volatility metrics such as l_iv30 or term structure changes.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1452 signal days, hit 51.6% (always-long 56.1%), strategy -2.6 bps/day vs +2.1 for the same average exposure held constantly -> timing adds -4.7 bps/day, t=-1.82, positive in 4/9 years
How: long/short on `sign( (iv30 - lag(iv30,1)) * (term - lag(term,1)) )` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]