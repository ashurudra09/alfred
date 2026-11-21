# Hard multi-step suite: alfred-2b-v4c-q8 (124 tasks)

2026-11-21T16:34:37, commit `d014e96`

- **Pass rate: 104/124 (83.9%)**
- 1 trial(s) per task at temperature 0.0, tool list current; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 23.27 s

| Tag | Passed |
|---|---|
| act_on_list | 2/8 |
| all_except | 6/7 |
| ask_then_act | 5/7 |
| bulk_rename | 5/8 |
| compare_files | 6/8 |
| conditional_act | 5/8 |
| count_and_size | 7/7 |
| deadline_reminder | 7/8 |
| decline_then_continue | 7/7 |
| exact_phrase | 5/5 |
| filtered_bulk | 7/7 |
| find_then_act | 7/7 |
| held_out | 25/40 |
| memory_then_act | 7/7 |
| new_capability | 22/25 |
| notes_and_reminders | 7/7 |
| nothing_matches | 5/5 |
| pick_extreme | 5/7 |
| read_then_compute | 7/7 |
| recover_empty | 7/7 |
| shared | 79/84 |
| topic_find | 5/5 |
| topic_then_act | 5/5 |
| topic_then_read | 2/5 |
| two_part | 7/7 |

Failures:

- `pick_extreme-0000`: turn 1: the answer lacks [('manual_2023.png',)] (calls: search_files, move_to_recycle_bin)
- `pick_extreme-0004`: turn 1: the answer lacks [('invoice_old.png',)] (calls: search_files, move_file)
- `all_except-0000`: files differ: missing ['desktop/archive/lease_june.jpg', 'desktop/archive/minutes_final.pptx', 'desktop/archive/newsletter_2025.pdf'], unexpected ['downloads/scans/lease_june.jpg', 'downloads/scans/minutes_final.pptx', 'downloads/scans/newsletter_2025.pdf'] (calls: none)
- `ask_then_act-0001`: files differ: missing [], unexpected ['desktop/travel/newsletter_q3.pdf'] (calls: move_to_recycle_bin, move_to_recycle_bin)
- `ask_then_act-0003`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\12248\60\Documents\inbox\invoice_revised.pdf → C:\work\interview prep\projects\alfred\runs\sb\12248\60\Downloads\invoice_revised.pdf) (calls: search_files, move_file, move_file)
- `compare_files-0002`: turn 1: the answer lacks [2288] (calls: read_file, read_file)
- `compare_files-0004`: turn 1: the answer lacks [1693] (calls: read_file, read_file)
- `act_on_list-0000`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\12248\93\Desktop\brochure_list.txt → C:\work\interview prep\projects\alfred\runs\sb\12248\93\Downloads\scans\brochure_list.txt) (calls: read_file, move_file)
- `act_on_list-0002`: files differ: missing ['desktop/scans/itinerary_signed.docx', 'desktop/scans/newsletter_old.xlsx', 'desktop/scans/thesis_draft.png'], unexpected ['documents/clients/itinerary_signed.docx', 'documents/clients/newsletter_old.xlsx', 'documents/clients/thesis_draft.png'] (calls: read_file, move_file, move_file, move_file)
- `act_on_list-0003`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\12248\96\Documents\itinerary_list.txt → C:\work\interview prep\projects\alfred\runs\sb\12248\96\Downloads\clients\itinerary_list.txt) (calls: read_file, move_file)
- `act_on_list-0005`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\12248\98\Desktop\ledger_list.txt → C:\work\interview prep\projects\alfred\runs\sb\12248\98\Documents\clients\ledger_list.txt) (calls: read_file, move_file)
- `act_on_list-0006`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\12248\99\Desktop\thesis_list.txt → C:\work\interview prep\projects\alfred\runs\sb\12248\99\Documents\coursework\thesis_list.txt) (calls: read_file, move_file)
- `act_on_list-0007`: files differ: missing ['documents/clients/brochure_march.pdf', 'documents/clients/invoice_june.jpg', 'documents/clients/itinerary_signed.xlsx'], unexpected ['downloads/keepsakes/brochure_march.pdf', 'downloads/keepsakes/invoice_june.jpg', 'downloads/keepsakes/itinerary_signed.xlsx'] (calls: none)
- `deadline_reminder-0004`: reminders: expected ['2027-03-03 09:00'], set [] (calls: read_file, set_reminder)
- `conditional_act-0004`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0007`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\12248\116\Documents\receipts → C:\work\interview prep\projects\alfred\runs\sb\12248\116\Desktop\receipts.zip) (calls: search_files, zip_folder)
- `bulk_rename-0002`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\12248\119\Documents\travel\ledger_2025.xlsx → quartz_2025.xlsx) (calls: list_directory, rename_file, rename_file, rename_file)
- `bulk_rename-0004`: files differ: missing ['documents/inbox/cobalt_newsletter_revised.pptx'], unexpected ['documents/inbox/newsletter_revised.pptx'] (calls: list_directory, rename_file, rename_file, rename_file, rename_file)
- `bulk_rename-0007`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\12248\124\Downloads\shared\manual_march.docx → falcon_march.docx) (calls: list_directory, rename_file, rename_file, rename_file)
- `topic_then_read-0000`: turn 1: the answer lacks [72] (calls: search_notes, recall)
- `topic_then_read-0001`: turn 1: the answer lacks [4200] (calls: search_notes, search_notes)
- `topic_then_read-0002`: turn 1: the answer lacks ['flowerpot'] (calls: search_by_meaning)
