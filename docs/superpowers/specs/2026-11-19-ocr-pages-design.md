# Explorer OCR reliability and page selection

The user reports Explorer OCR fails with Windows access denied and requests a
"Wytnij strony" action with keep/remove modes. They explicitly define forgiving
input: extract numbers and range hyphens, ignoring other text between them.

## Existing behavior and confirmed cause

The 465-page local reproduction fails replacing report.partial with report.json.
The dialog polls this file while the worker rapidly reports already searchable
pages; Windows forbids replacing a file while its reader lacks delete sharing.
The same worker succeeds without the polling dialog. Source PDF is unchanged.

## Approach and decisions

Keep the atomic JSON protocol and retry transient PermissionError with a bounded
deadline; unlike non-atomic overwrites this never exposes partial JSON. Preserve
the existing OCR/native-text policy, in-place commit guards and local backups.
The user confirmed this exact error, so no new OCR engine or re-OCR policy is needed.

Use the existing project page-state list and undo stack for trimming. A separate
PDF rewrite tool would lose editable objects and create a second save workflow.
Add one dialog reached through Strony and the page sidebar, with two visible
radio choices, free text, live normalized selection and remaining/deleted counts.
Keep source order, deduplicate selections, use 1-based physical PDF positions.
Treat ASCII hyphens and common pasted dash variants as inclusive range markers.
Reject zero/out-of-range/descending or incomplete ranges and an empty result.
Unknown words and punctuation do not join separate runs of digits.
Original PDF stays untouched until normal export; Ctrl+Z restores removed pages,
objects, rotations and margins. Project save and PDF export use current pages.

## Verification and delivery

Regression with a real Windows reader holding report.json open, real dialog with
many native pages, parser boundaries, keep/remove undo/redo and saved outputs.
Reproduce on a local copy of the user's book; no user documents enter GitHub.
Check static Qt widget captures, not Windows screen capture (user rejects border).
Publish 0.4.0 with normal installers and verified updater, as authorized earlier.
