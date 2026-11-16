# Hard multi-step suite: alfred-2b-v3-q4 (124 tasks)

2026-11-17T01:01:08, commit `32011d2`

- **Pass rate: 71/124 (57.3%)**
- 1 trial(s) per task at temperature 0.0, tool list 1.2; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 17.1 s

| Tag | Passed |
|---|---|
| act_on_list | 0/8 |
| all_except | 5/7 |
| ask_then_act | 5/7 |
| bulk_rename | 0/8 |
| compare_files | 6/8 |
| conditional_act | 4/8 |
| count_and_size | 7/7 |
| deadline_reminder | 8/8 |
| decline_then_continue | 4/7 |
| filtered_bulk | 7/7 |
| find_then_act | 2/7 |
| held_out | 18/40 |
| memory_then_act | 2/7 |
| notes_and_reminders | 4/7 |
| pick_extreme | 4/7 |
| read_then_compute | 7/7 |
| recover_empty | 0/7 |
| shared | 53/84 |
| two_part | 6/7 |

Failures:

- `find_then_act-0001`: files differ: missing ['downloads/payslip_q1.xlsx'], unexpected [] (calls: recall, search_files)
- `find_then_act-0003`: files differ: missing ['downloads/survey_2023.pdf'], unexpected ['desktop/scans/survey_2023.pdf'] (calls: search_files, search_files)
- `find_then_act-0004`: files differ: missing ['desktop/warranty_2023.xlsx'], unexpected [] (calls: search_files)
- `find_then_act-0005`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\7996\3\Documents\scans\brochure_q3.xlsx to the Recycle Bin (restorable)) (calls: search_files, move_to_recycle_bin)
- `find_then_act-0006`: files differ: missing ['desktop/warranty_2023.pptx'], unexpected ['documents/receipts/warranty_2023.pptx'] (calls: recall)
- `pick_extreme-0000`: turn 1: the answer lacks [('manual_2023.png',)] (calls: search_files, move_to_recycle_bin)
- `pick_extreme-0004`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\22908\10\Downloads\travel\ledger_draft.pptx → C:\work\interview prep\projects\alfred\runs\sb\22908\10\Documents\ledger_draft.pptx) (calls: search_files, move_file)
- `pick_extreme-0006`: files differ: missing [], unexpected ['desktop/inbox/contract_revised.png'] (calls: search_files)
- `all_except-0000`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\7996\11\Downloads\scans → C:\work\interview prep\projects\alfred\runs\sb\7996\11\Desktop\archive\scans) (calls: move_file)
- `all_except-0002`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\7996\12\Desktop\receipts → C:\work\interview prep\projects\alfred\runs\sb\7996\12\Downloads\shared\receipts) (calls: move_file)
- `memory_then_act-0002`: files differ: missing ['downloads/archive/recipe_q3/invoice_final.pdf'], unexpected ['documents/invoice_final.pdf'] (calls: move_file)
- `memory_then_act-0003`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\22908\20\Documents\housing\recipe_2023 → C:\work\interview prep\projects\alfred\runs\sb\22908\20\Documents\housing\recipe_2023.zip) (calls: recall, zip_folder)
- `memory_then_act-0004`: turn 1: the answer lacks ['thesis_q2.xlsx', 'invoice_2024.jpg', 'recipe_old.jpg'] (calls: none)
- `memory_then_act-0005`: files differ: missing ['downloads/receipts/lease_revised/permit_q3.png'], unexpected ['documents/permit_q3.png'] (calls: move_file)
- `memory_then_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: zip_folder)
- `two_part-0001`: files differ: missing ['downloads/scans/transcript_q1.txt'], unexpected ['downloads/scans/transcript_october.txt'] (calls: read_file, rename_file)
- `recover_empty-0000`: files differ: missing ['downloads/brochure_revised.txt'], unexpected ['documents/travel/brochure_revised.txt'] (calls: search_files)
- `recover_empty-0001`: turn 1: the answer lacks ['recipe_2025.md'] (calls: search_files)
- `recover_empty-0002`: files differ: missing ['downloads/payslip_final.txt'], unexpected ['documents/archive/payslip_final.txt'] (calls: search_files)
- `recover_empty-0003`: turn 1: the answer lacks ['ledger_2024.md'] (calls: search_files)
- `recover_empty-0004`: files differ: missing ['desktop/lease_june.txt'], unexpected ['downloads/shared/lease_june.txt'] (calls: search_files)
- `recover_empty-0005`: turn 1: the answer lacks ['syllabus_q3.txt'] (calls: search_files)
- `recover_empty-0006`: files differ: missing ['downloads/warranty_old.md'], unexpected ['desktop/shared/warranty_old.md'] (calls: search_files)
- `ask_then_act-0001`: files differ: missing [], unexpected ['desktop/travel/newsletter_q3.pdf'] (calls: move_to_recycle_bin, move_to_recycle_bin)
- `ask_then_act-0002`: turn 1: did not ask (calls: copy_file, search_files)
- `decline_then_continue-0002`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: move_to_recycle_bin)
- `decline_then_continue-0004`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: none)
- `decline_then_continue-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: move_to_recycle_bin)
- `notes_and_reminders-0000`: notes: expected [('transcript gate', 'QUARTZ-9770')], made [] (calls: none)
- `notes_and_reminders-0002`: notes: expected [('contract gate', 'FALCON-7584')], made [] (calls: none)
- `notes_and_reminders-0004`: notes: expected [('minutes gate', 'SAFFRON-7911')], made [] (calls: none)
- `compare_files-0002`: turn 1: the answer lacks [2288] (calls: read_file, read_file)
- `compare_files-0004`: turn 1: the answer lacks [1693] (calls: read_file, read_file)
- `act_on_list-0000`: files differ: missing ['downloads/scans/invoice_draft.jpg', 'downloads/scans/ledger_old.png', 'downloads/scans/permit_final.jpg'], unexpected ['documents/receipts/invoice_draft.jpg', 'documents/receipts/ledger_old.png', 'documents/receipts/permit_final.jpg'] (calls: read_file, move_file, move_file, move_file)
- `act_on_list-0001`: files differ: missing ['documents/keepsakes/contract_revised.xlsx', 'documents/keepsakes/minutes_signed.docx', 'documents/keepsakes/syllabus_march.pptx'], unexpected ['downloads/clients/contract_revised.xlsx', 'downloads/clients/minutes_signed.docx', 'downloads/clients/syllabus_march.pptx'] (calls: none)
- `act_on_list-0002`: files differ: missing ['desktop/scans/itinerary_signed.docx', 'desktop/scans/newsletter_old.xlsx', 'desktop/scans/thesis_draft.png'], unexpected ['documents/clients/itinerary_signed.docx', 'documents/clients/newsletter_old.xlsx', 'documents/clients/thesis_draft.png'] (calls: read_file, move_file, move_file, move_file)
- `act_on_list-0003`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\7996\48\Documents\itinerary_list.txt → C:\work\interview prep\projects\alfred\runs\sb\7996\48\Downloads\clients\itinerary_list.txt) (calls: read_file, move_file)
- `act_on_list-0004`: files differ: missing ['desktop/coursework/invoice_q2.jpg', 'desktop/coursework/permit_october.xlsx', 'desktop/coursework/proposal_old.docx'], unexpected ['downloads/shared/invoice_q2.jpg', 'downloads/shared/permit_october.xlsx', 'downloads/shared/proposal_old.docx'] (calls: none)
- `act_on_list-0005`: files differ: missing ['documents/clients/manual_final.pptx', 'documents/clients/minutes_signed.pdf', 'documents/clients/roadmap_signed.docx'], unexpected ['downloads/housing/manual_final.pptx', 'downloads/housing/minutes_signed.pdf', 'downloads/housing/roadmap_signed.docx'] (calls: read_file, move_file, move_file, move_file)
- `act_on_list-0006`: files differ: missing ['documents/coursework/blueprint_june.pdf', 'documents/coursework/contract_revised.xlsx', 'documents/coursework/syllabus_2025.png'], unexpected ['desktop/housing/blueprint_june.pdf', 'desktop/housing/contract_revised.xlsx', 'desktop/housing/syllabus_2025.png'] (calls: read_file, move_file, move_file, move_file)
- `act_on_list-0007`: files differ: missing ['documents/clients/brochure_march.pdf', 'documents/clients/invoice_june.jpg', 'documents/clients/itinerary_signed.xlsx'], unexpected ['downloads/keepsakes/brochure_march.pdf', 'downloads/keepsakes/invoice_june.jpg', 'downloads/keepsakes/itinerary_signed.xlsx'] (calls: none)
- `conditional_act-0000`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0002`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0004`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `bulk_rename-0000`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\22908\59\Desktop\shared\permit_october.xlsx → quartz_2024.xlsx) (calls: list_directory, rename_file)
- `bulk_rename-0001`: files differ: missing ['documents/keepsakes/saffron_itinerary_final.png', 'documents/keepsakes/saffron_proposal_2025.docx', 'documents/keepsakes/saffron_transcript_2024.docx'], unexpected ['documents/keepsakes/itinerary_final.png', 'documents/keepsakes/proposal_2025.docx', 'documents/keepsakes/transcript_2024.docx'] (calls: none)
- `bulk_rename-0002`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\22908\60\Documents\travel\ledger_2025.xlsx → quartz_2025.xlsx) (calls: list_directory, rename_file)
- `bulk_rename-0003`: files differ: missing ['downloads/travel/lantern_brochure_draft.png', 'downloads/travel/lantern_minutes_q1.png', 'downloads/travel/lantern_recipe_2025.pdf'], unexpected ['downloads/travel/brochure_draft.png', 'downloads/travel/minutes_q1.png', 'downloads/travel/recipe_2025.pdf'] (calls: none)
- `bulk_rename-0004`: files differ: missing ['documents/inbox/cobalt_brochure_2025.png', 'documents/inbox/cobalt_ledger_2024.png', 'documents/inbox/cobalt_newsletter_revised.pptx'], unexpected ['documents/inbox/brochure_2025.png', 'documents/inbox/ledger_2024.png', 'documents/inbox/newsletter_revised.pptx'] (calls: none)
- `bulk_rename-0005`: files differ: missing ['downloads/inbox/harbor_contract_signed.png', 'downloads/inbox/harbor_itinerary_q1.docx', 'downloads/inbox/harbor_manual_signed.pdf'], unexpected ['downloads/inbox/contract_signed.png', 'downloads/inbox/itinerary_q1.docx', 'downloads/inbox/manual_signed.pdf'] (calls: none)
- `bulk_rename-0006`: files differ: missing ['documents/receipts/maple_blueprint_final.pptx', 'documents/receipts/maple_blueprint_q2.pdf', 'documents/receipts/maple_recipe_q1.png'], unexpected ['documents/receipts/blueprint_final.pptx', 'documents/receipts/blueprint_q2.pdf', 'documents/receipts/recipe_q1.png'] (calls: none)
- `bulk_rename-0007`: files differ: missing ['downloads/shared/falcon_newsletter_final.pdf', 'downloads/shared/falcon_survey_draft.xlsx'], unexpected ['downloads/shared/newsletter_final.pdf', 'downloads/shared/survey_draft.xlsx'] (calls: list_directory, rename_file, rename_file)
