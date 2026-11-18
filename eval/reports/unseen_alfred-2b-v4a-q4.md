# Hard multi-step suite: alfred-2b-v4a-q4 (30 tasks)

2026-11-18T12:00:53, commit `224f7d4`

- **Pass rate: 20/30 (66.7%)**
- 1 trial(s) per task at temperature 0.0, tool list current; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model not running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 12.71 s

| Tag | Passed |
|---|---|
| clip_code | 4/5 |
| convert_to_note | 5/5 |
| count_then_copy | 5/5 |
| finish_todo | 1/5 |
| same_or_not | 1/5 |
| todos_from_file | 4/5 |
| unseen | 20/30 |

Failures:

- `unseen_clip_code-0002`: clipboard: expected 'INDIGO-5293', holds 'Booking reference: INDIGO-5293' (calls: read_file, clipboard_set)
- `unseen_todos_from_file-0001`: to-do list: expected [('library books', False), ('contact lenses', False), ('home insurance', False)], holds [] (calls: none)
- `unseen_same_or_not-0000`: files differ: missing [], unexpected ['downloads/archive/survey_copy.txt'] (calls: hashFile, hashFile)
- `unseen_same_or_not-0001`: turn 1: the answer lacks [('not', 'differ', 'different', "aren't", "isn't")] (calls: copy_file)
- `unseen_same_or_not-0002`: files differ: missing [], unexpected ['downloads/coursework/newsletter_copy.txt'] (calls: hashFile, hashFile)
- `unseen_same_or_not-0004`: files differ: missing [], unexpected ['downloads/inbox/blueprint_copy.txt'] (calls: hashFile, hashFile)
- `unseen_finish_todo-0000`: to-do list: expected [('send the invoice', True), ('call the landlord', False), ('fix the bike light', False)], holds [('send the invoice', False), ('call the landlord', False), ('fix the bike light', True)] (calls: todo_done, create_note)
- `unseen_finish_todo-0001`: to-do list: expected [('post the birthday card', False), ('fix the bike light', True), ('back up the laptop', False)], holds [('post the birthday card', True), ('fix the bike light', False), ('back up the laptop', False)] (calls: todo_done, create_note)
- `unseen_finish_todo-0003`: notes: expected [('falcon', ('done', 'finished', 'complete', 'ticked'))], made [('falcon', 'post the birthday card')] (calls: todo_done, create_note)
- `unseen_finish_todo-0004`: to-do list: expected [('call the landlord', False), ('send the invoice', True), ('post the birthday card', False)], holds [('call the landlord', False), ('send the invoice', False), ('post the birthday card', True)] (calls: todo_done, create_note)
