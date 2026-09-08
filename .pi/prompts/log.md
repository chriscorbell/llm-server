---
description: Start a docs/log experiment entry from the template
argument-hint: "<topic-slug> [hypothesis]"
---
Create a new experiment entry for this repository.

1. Run `date +%F` to get today's date.
2. Copy `docs/log/TEMPLATE.md` to `docs/log/<date>-$1.md`.
3. Fill in the title, set Status to "in progress", the Profile to the one in STATUS.md, and write the hypothesis: ${@:2}
4. Under Configuration, state the single variable being changed relative to the current STATUS.md state. Leave the command block for me to fill unless it is already clear from the hypothesis.
5. Delete measurement rows that this experiment will not measure. Do not invent numbers.

Show me the file path and the hypothesis paragraph when done. Do not edit STATUS.md yet.
