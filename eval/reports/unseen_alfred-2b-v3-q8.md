# Hard multi-step suite: alfred-2b-v3-q8 (30 tasks)

2026-11-21T21:26:37, commit `2ec2306`

- **Pass rate: 24/30 (80.0%)**
- 1 trial(s) per task at temperature 0.0, tool list 1.2; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model not running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 13.16 s

| Tag | Passed |
|---|---|
| clip_code | 5/5 |
| convert_to_note | 4/5 |
| count_then_copy | 3/5 |
| finish_todo | 3/5 |
| same_or_not | 4/5 |
| todos_from_file | 5/5 |
| unseen | 24/30 |

Failures:

- `unseen_count_then_copy-0000`: turn 1: the answer lacks [52] (calls: copy_file, search_file_contents)
- `unseen_count_then_copy-0004`: turn 1: the answer lacks [88] (calls: copy_file, search_file_contents)
- `unseen_same_or_not-0000`: files differ: missing [], unexpected ['downloads/archive/survey_copy.txt'] (calls: files-differ)
- `unseen_finish_todo-0001`: notes: expected [('falcon', ('done', 'finished', 'complete', 'ticked'))], made [('falcon', 'fix the bike light')] (calls: todo_done, create_note)
- `unseen_finish_todo-0004`: to-do list: expected [('call the landlord', False), ('send the invoice', True), ('post the birthday card', False)], holds [('call the landlord', True), ('send the invoice', False), ('post the birthday card', False)] (calls: todo_done, create_note)
- `unseen_convert_to_note-0001`: notes: expected [('falcon', (202.78, 202.8))], made [('falcon', 'Route length in km: 78.292746')] (calls: read_file, calculate, create_note)
