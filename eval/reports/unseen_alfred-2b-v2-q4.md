# Hard multi-step suite: alfred-2b-v2-q4 (30 tasks)

2026-11-17T21:39:47, commit `83cb0eb`

- **Pass rate: 13/30 (43.3%)**
- 1 trial(s) per task at temperature 0.0, tool list 1.2; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model not running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 8.0 s

| Tag | Passed |
|---|---|
| clip_code | 0/5 |
| convert_to_note | 2/5 |
| count_then_copy | 5/5 |
| finish_todo | 2/5 |
| same_or_not | 2/5 |
| todos_from_file | 2/5 |
| unseen | 13/30 |

Failures:

- `unseen_clip_code-0000`: clipboard: expected 'LANTERN-6671', holds 'booking reference 12345678' (calls: clipboard_set)
- `unseen_clip_code-0001`: clipboard: expected 'FALCON-2619', holds 'booking reference 12345678' (calls: clipboard_set)
- `unseen_clip_code-0002`: clipboard: expected 'INDIGO-5293', holds 'booking reference: 84921' (calls: clipboard_set)
- `unseen_clip_code-0003`: clipboard: expected 'MAPLE-4327', holds 'ABC123456' (calls: clipboard_set)
- `unseen_clip_code-0004`: clipboard: expected 'SAFFRON-3449', holds 'ABC123456' (calls: clipboard_set)
- `unseen_todos_from_file-0002`: to-do list: expected [('water bill', False), ('library books', False), ('home insurance', False)], holds [('Review every job in Desktop\\scans\\contract_q1.txt', False)] (calls: todo_add)
- `unseen_todos_from_file-0003`: to-do list: expected [('water bill', False), ('library books', False), ('parking permit', False)], holds [('Apply for every job listed in Desktop\\shared\\permit_q3.txt', False)] (calls: todo_add)
- `unseen_todos_from_file-0004`: to-do list: expected [('contact lenses', False), ('boiler service', False), ('home insurance', False)], holds [('Apply for job in manual_march.txt', False)] (calls: todo_add)
- `unseen_same_or_not-0000`: files differ: missing [], unexpected ['downloads/archive/survey_copy.txt'] (calls: files-differ)
- `unseen_same_or_not-0002`: files differ: missing [], unexpected ['downloads/coursework/newsletter_copy.txt'] (calls: files-differ)
- `unseen_same_or_not-0004`: files differ: missing [], unexpected ['downloads/inbox/blueprint_copy.txt'] (calls: files-differ)
- `unseen_finish_todo-0001`: to-do list: expected [('post the birthday card', False), ('fix the bike light', True), ('back up the laptop', False)], holds [('post the birthday card', True), ('fix the bike light', False), ('back up the laptop', False)] (calls: todo_done, create_note)
- `unseen_finish_todo-0002`: notes: expected [('indigo', ('done', 'finished', 'complete', 'ticked'))], made [('indigo', 'post the birthday card')] (calls: todo_done, create_note)
- `unseen_finish_todo-0004`: to-do list: expected [('call the landlord', False), ('send the invoice', True), ('post the birthday card', False)], holds [('call the landlord', True), ('send the invoice', False), ('post the birthday card', False)] (calls: todo_done, create_note)
- `unseen_convert_to_note-0000`: notes: expected [('maple', (151.28, 151.3))], made [('maple', '12345 mi = 19867.4 km')] (calls: convertUnits, create_note)
- `unseen_convert_to_note-0003`: notes: expected [('harbor', (91.73, 91.7))], made [('harbor', '19867.4 km')] (calls: convertUnits, create_note)
- `unseen_convert_to_note-0004`: notes: expected [('falcon', (62.76, 62.8))], made [('falcon', '12345 mi = 19867.4 km')] (calls: convertUnits, create_note)
