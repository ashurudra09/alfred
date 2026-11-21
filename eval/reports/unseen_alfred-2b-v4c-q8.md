# Hard multi-step suite: alfred-2b-v4c-q8 (30 tasks)

2026-11-21T20:42:14, commit `2ec2306`

- **Pass rate: 25/30 (83.3%)**
- 1 trial(s) per task at temperature 0.0, tool list current; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model not running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 12.56 s

| Tag | Passed |
|---|---|
| clip_code | 5/5 |
| convert_to_note | 5/5 |
| count_then_copy | 5/5 |
| finish_todo | 2/5 |
| same_or_not | 3/5 |
| todos_from_file | 5/5 |
| unseen | 25/30 |

Failures:

- `unseen_same_or_not-0000`: files differ: missing [], unexpected ['downloads/archive/survey_copy.txt'] (calls: read_file, read_file)
- `unseen_same_or_not-0002`: files differ: missing [], unexpected ['downloads/coursework/newsletter_copy.txt'] (calls: read_file, read_file)
- `unseen_finish_todo-0001`: notes: expected [('falcon', ('done', 'finished', 'complete', 'ticked'))], made [('falcon', 'Fixed the bike light.')] (calls: todo_done, create_note)
- `unseen_finish_todo-0003`: notes: expected [('falcon', ('done', 'finished', 'complete', 'ticked'))], made [('falcon', 'post the birthday card')] (calls: todo_done, create_note)
- `unseen_finish_todo-0004`: to-do list: expected [('call the landlord', False), ('send the invoice', True), ('post the birthday card', False)], holds [('call the landlord', True), ('send the invoice', False), ('post the birthday card', False)] (calls: todo_done, create_note)
