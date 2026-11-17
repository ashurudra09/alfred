# Hard multi-step suite: alfred-2b-v3-q4 (30 tasks)

2026-11-17T20:58:24, commit `80018f1`

- **Pass rate: 18/30 (60.0%)**
- 1 trial(s) per task at temperature 0.0, tool list 1.2; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model not running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 24.73 s

| Tag | Passed |
|---|---|
| clip_code | 5/5 |
| convert_to_note | 3/5 |
| count_then_copy | 3/5 |
| finish_todo | 2/5 |
| same_or_not | 0/5 |
| todos_from_file | 5/5 |
| unseen | 18/30 |

Failures:

- `unseen_count_then_copy-0000`: turn 1: the answer lacks [52] (calls: copy_file, recall)
- `unseen_count_then_copy-0004`: turn 1: the answer lacks [88] (calls: copy_file, recall)
- `unseen_same_or_not-0000`: files differ: missing [], unexpected ['downloads/archive/survey_copy.txt'] (calls: hashFile, hashFile)
- `unseen_same_or_not-0001`: turn 1: the answer lacks [('not', 'differ', 'different', "aren't", "isn't")] (calls: copy_file)
- `unseen_same_or_not-0002`: files differ: missing [], unexpected ['downloads/coursework/newsletter_copy.txt'] (calls: copy_file)
- `unseen_same_or_not-0003`: turn 1: the answer lacks [('not', 'differ', 'different', "aren't", "isn't")] (calls: copy_file)
- `unseen_same_or_not-0004`: files differ: missing [], unexpected ['downloads/inbox/blueprint_copy.txt'] (calls: copy_file)
- `unseen_finish_todo-0001`: notes: expected [('falcon', ('done', 'finished', 'complete', 'ticked'))], made [('falcon', 'Bike light fixed')] (calls: todo_done, create_note)
- `unseen_finish_todo-0003`: notes: expected [('falcon', ('done', 'finished', 'complete', 'ticked'))], made [('falcon', 'post the birthday card')] (calls: todo_done, create_note)
- `unseen_finish_todo-0004`: to-do list: expected [('call the landlord', False), ('send the invoice', True), ('post the birthday card', False)], holds [('call the landlord', True), ('send the invoice', False), ('post the birthday card', False)] (calls: todo_done, create_note)
- `unseen_convert_to_note-0001`: notes: expected [('falcon', (202.78, 202.8))], made [('falcon', 'Route length in km: 78.29 km')] (calls: read_file, calculate, create_note)
- `unseen_convert_to_note-0002`: notes: expected [('falcon', (88.51, 88.5))], made [('falcon', 'Route length in km: 15.27777778')] (calls: read_file, calculate, create_note)
