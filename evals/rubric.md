# Rubric

Each draft is scored yes or no on five items. A draft passes with 4 of 5, and item 3 is always required.

| # | Item | Yes when |
| --- | --- | --- |
| 1 | Goal | It restates the client's goal and covers every explicit requirement |
| 2 | Specific | It uses at least two details that appear only in this post |
| 3 | Honest proof (required) | Every claim (past work, results, who does the work, availability, attachments) traces to the profile or the post, and new work is called new |
| 4 | Plan | It names concrete first steps, not a generic process |
| 5 | Ask | It ends with one clear question or next step, inside the platform's length limit and the post's format instructions |

## How drafts are scored

- I score every v1 and v2 draft by hand.
- An AI judge scores the same drafts with the v1 and v2 labels removed. The judge is a different model from the ones that drafted, so no model grades its own work.
- Calibration: I score 6 drafts before the judge sees them. Agreement is reported per item, and items where the judge disagrees with me are scored by hand only.
- Unsupported claims are always counted by hand. The claim check is measured against those counts and never used as the score.

## Checked against real drafts

On Day 1 the rubric was tried on eight real drafts: five v1 generated for real Upwork jobs and three from plain ChatGPT ([baseline](baseline.md)). All five items told drafts apart or caught real misses, so all five stay.

- Item 1 picked up two posts with explicit asks (availability; five numbered questions) that need a point-by-point answer.
- Item 3 originally covered past work only. v1 wrote in an agency's voice and mentioned a video walkthrough, and one post asked who would personally do the work. So item 3 now also covers who does the work, availability and attachments.
- Item 2 passed on all eight, so it's the weakest at telling drafts apart. Day 4 checks whether it still passes everything.

## Notes

- Platform length limits live in config from Day 2.
- T06 tests item 1 on a 2,000-word spec, where the length limit pulls the other way ([decision log](../docs/decision-log.md), row 11).
