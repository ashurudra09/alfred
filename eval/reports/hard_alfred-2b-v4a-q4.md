# Hard multi-step suite: alfred-2b-v4a-q4 (124 tasks)

2026-11-18T12:33:56, commit `224f7d4`

- **Pass rate: 75/124 (60.5%)**
- 1 trial(s) per task at temperature 0.0, tool list current; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 10.21 s

| Tag | Passed |
|---|---|
| act_on_list | 0/8 |
| all_except | 4/7 |
| ask_then_act | 4/7 |
| bulk_rename | 0/8 |
| compare_files | 6/8 |
| conditional_act | 4/8 |
| count_and_size | 7/7 |
| deadline_reminder | 8/8 |
| decline_then_continue | 7/7 |
| exact_phrase | 5/5 |
| filtered_bulk | 5/7 |
| find_then_act | 2/7 |
| held_out | 18/40 |
| memory_then_act | 3/7 |
| new_capability | 22/25 |
| notes_and_reminders | 7/7 |
| nothing_matches | 3/5 |
| pick_extreme | 3/7 |
| read_then_compute | 7/7 |
| recover_empty | 3/7 |
| shared | 57/84 |
| topic_find | 5/5 |
| topic_then_act | 5/5 |
| topic_then_read | 4/5 |
| two_part | 5/7 |

Failures:

- `find_then_act-0000`: files differ: missing ['documents/newsletter_2025.xlsx'], unexpected ['downloads/clients/newsletter_2025.xlsx'] (calls: search_by_meaning)
- `find_then_act-0001`: files differ: missing ['downloads/payslip_q1.xlsx'], unexpected [] (calls: search_files)
- `find_then_act-0003`: files differ: missing ['downloads/survey_2023.pdf'], unexpected ['desktop/scans/survey_2023.pdf'] (calls: search_by_meaning)
- `find_then_act-0004`: files differ: missing ['desktop/warranty_2023.xlsx'], unexpected [] (calls: search_files)
- `find_then_act-0006`: files differ: missing ['desktop/warranty_2023.pptx'], unexpected ['documents/receipts/warranty_2023.pptx'] (calls: search_by_meaning)
- `pick_extreme-0000`: turn 1: the answer lacks [('manual_2023.png',)] (calls: search_files, move_to_recycle_bin)
- `pick_extreme-0003`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\21024\18\Documents\travel\warranty_final.docx → C:\work\interview prep\projects\alfred\runs\sb\21024\18\Desktop\warranty_final.docx) (calls: search_files, move_file)
- `pick_extreme-0004`: turn 1: the answer lacks [('invoice_old.png',)] (calls: search_files, move_file)
- `pick_extreme-0005`: files differ: missing [], unexpected ['desktop/keepsakes/manual_q3.png'] (calls: disk_usage, disk_usage)
- `all_except-0000`: files differ: missing ['desktop/archive/lease_june.jpg', 'desktop/archive/minutes_final.pptx', 'desktop/archive/newsletter_2025.pdf'], unexpected ['downloads/scans/lease_june.jpg', 'downloads/scans/minutes_final.pptx', 'downloads/scans/newsletter_2025.pdf'] (calls: move_file)
- `all_except-0002`: files differ: missing ['downloads/shared/itinerary_final.jpg', 'downloads/shared/lease_june.xlsx', 'downloads/shared/thesis_old.pdf'], unexpected ['desktop/receipts/itinerary_final.jpg', 'desktop/receipts/lease_june.xlsx', 'desktop/receipts/thesis_old.pdf'] (calls: move_file)
- `all_except-0005`: files differ: missing ['documents/coursework/minutes_q2.pdf', 'documents/coursework/permit_draft.jpg', 'documents/coursework/thesis_signed.pptx'], unexpected ['downloads/shared/minutes_q2.pdf', 'downloads/shared/permit_draft.jpg', 'downloads/shared/thesis_signed.pptx'] (calls: list_directory, move_file)
- `filtered_bulk-0003`: files differ: missing ['downloads/scans/contract_october.pptx', 'downloads/scans/survey_draft.xlsx', 'downloads/scans/thesis_final.docx'], unexpected ['desktop/keepsakes/contract_october.pptx', 'desktop/keepsakes/survey_draft.xlsx', 'desktop/keepsakes/thesis_final.docx'] (calls: search_files)
- `filtered_bulk-0004`: files differ: missing ['downloads/inbox/lease_q3.xlsx', 'downloads/inbox/newsletter_q2.xlsx', 'downloads/inbox/transcript_q3.xlsx'], unexpected ['documents/archive/lease_q3.xlsx', 'documents/archive/newsletter_q2.xlsx', 'documents/archive/transcript_q3.xlsx'] (calls: search_files, move_file)
- `memory_then_act-0000`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: zip_folder)
- `memory_then_act-0002`: files differ: missing ['downloads/archive/recipe_q3/invoice_final.pdf'], unexpected ['documents/invoice_final.pdf'] (calls: move_file)
- `memory_then_act-0004`: turn 1: the answer lacks ['thesis_q2.xlsx', 'invoice_2024.jpg', 'recipe_old.jpg'] (calls: list_directory)
- `memory_then_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: zip_folder)
- `two_part-0001`: files differ: missing ['downloads/scans/transcript_q1.txt'], unexpected ['downloads/scans/transcript_october.txt'] (calls: search_file_contents)
- `two_part-0002`: turn 1: the answer lacks [3206.0] (calls: calculate, list_directory)
- `recover_empty-0000`: files differ: missing ['downloads/brochure_revised.txt'], unexpected ['documents/travel/brochure_revised.txt'] (calls: search_files)
- `recover_empty-0002`: files differ: missing ['downloads/payslip_final.txt'], unexpected ['documents/archive/payslip_final.txt'] (calls: search_files)
- `recover_empty-0004`: files differ: missing ['desktop/lease_june.txt'], unexpected ['downloads/shared/lease_june.txt'] (calls: search_files)
- `recover_empty-0006`: files differ: missing ['downloads/warranty_old.md'], unexpected ['desktop/shared/warranty_old.md'] (calls: search_files)
- `ask_then_act-0001`: files differ: missing [], unexpected ['desktop/travel/newsletter_q3.pdf'] (calls: move_to_recycle_bin, move_to_recycle_bin)
- `ask_then_act-0002`: turn 1: did not ask (calls: copy_file, search_files)
- `ask_then_act-0006`: turn 1: did not ask (calls: move_file, search_files, move_file)
- `compare_files-0002`: turn 1: the answer lacks [2288] (calls: read_file, read_file)
- `compare_files-0004`: turn 1: the answer lacks [1693] (calls: read_file, read_file)
- `act_on_list-0000`: files differ: missing ['downloads/scans/invoice_draft.jpg', 'downloads/scans/ledger_old.png', 'downloads/scans/permit_final.jpg'], unexpected ['documents/receipts/invoice_draft.jpg', 'documents/receipts/ledger_old.png', 'documents/receipts/permit_final.jpg'] (calls: none)
- `act_on_list-0001`: files differ: missing ['documents/keepsakes/contract_revised.xlsx', 'documents/keepsakes/minutes_signed.docx', 'documents/keepsakes/syllabus_march.pptx'], unexpected ['downloads/clients/contract_revised.xlsx', 'downloads/clients/minutes_signed.docx', 'downloads/clients/syllabus_march.pptx'] (calls: none)
- `act_on_list-0002`: files differ: missing ['desktop/scans/itinerary_signed.docx', 'desktop/scans/newsletter_old.xlsx', 'desktop/scans/thesis_draft.png'], unexpected ['documents/clients/itinerary_signed.docx', 'documents/clients/newsletter_old.xlsx', 'documents/clients/thesis_draft.png'] (calls: none)
- `act_on_list-0003`: files differ: missing ['downloads/clients/invoice_draft.pdf', 'downloads/clients/ledger_q2.png', 'downloads/clients/roadmap_2025.pptx'], unexpected ['desktop/scans/invoice_draft.pdf', 'desktop/scans/ledger_q2.png', 'desktop/scans/roadmap_2025.pptx'] (calls: none)
- `act_on_list-0004`: files differ: missing ['desktop/coursework/invoice_q2.jpg', 'desktop/coursework/permit_october.xlsx', 'desktop/coursework/proposal_old.docx'], unexpected ['downloads/shared/invoice_q2.jpg', 'downloads/shared/permit_october.xlsx', 'downloads/shared/proposal_old.docx'] (calls: none)
- `act_on_list-0005`: files differ: missing ['documents/clients/manual_final.pptx', 'documents/clients/minutes_signed.pdf', 'documents/clients/roadmap_signed.docx'], unexpected ['downloads/housing/manual_final.pptx', 'downloads/housing/minutes_signed.pdf', 'downloads/housing/roadmap_signed.docx'] (calls: none)
- `act_on_list-0006`: files differ: missing ['documents/coursework/blueprint_june.pdf', 'documents/coursework/contract_revised.xlsx', 'documents/coursework/syllabus_2025.png'], unexpected ['desktop/housing/blueprint_june.pdf', 'desktop/housing/contract_revised.xlsx', 'desktop/housing/syllabus_2025.png'] (calls: none)
- `act_on_list-0007`: files differ: missing ['documents/clients/brochure_march.pdf', 'documents/clients/invoice_june.jpg', 'documents/clients/itinerary_signed.xlsx'], unexpected ['downloads/keepsakes/brochure_march.pdf', 'downloads/keepsakes/invoice_june.jpg', 'downloads/keepsakes/itinerary_signed.xlsx'] (calls: none)
- `conditional_act-0000`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\21024\109\Documents\scans → C:\work\interview prep\projects\alfred\runs\sb\21024\109\Documents\scans.zip) (calls: search_files, zip_folder)
- `conditional_act-0004`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\21024\113\Downloads\scans → C:\work\interview prep\projects\alfred\runs\sb\21024\113\Downloads\scans.zip) (calls: search_files, zip_folder)
- `conditional_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0007`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\21024\116\Documents\receipts → C:\work\interview prep\projects\alfred\runs\sb\21024\116\Desktop\receipts.zip) (calls: search_files, zip_folder)
- `bulk_rename-0000`: files differ: missing ['desktop/shared/quartz_permit_october.xlsx', 'desktop/shared/quartz_recipe_2024.docx', 'desktop/shared/quartz_recipe_2024.jpg'], unexpected ['desktop/shared/permit_october.xlsx', 'desktop/shared/recipe_2024.docx', 'desktop/shared/recipe_2024.jpg'] (calls: list_directory, rename_file)
- `bulk_rename-0001`: files differ: missing ['documents/keepsakes/saffron_itinerary_final.png', 'documents/keepsakes/saffron_proposal_2025.docx', 'documents/keepsakes/saffron_transcript_2024.docx'], unexpected ['documents/keepsakes/itinerary_final.png', 'documents/keepsakes/proposal_2025.docx', 'documents/keepsakes/transcript_2024.docx'] (calls: none)
- `bulk_rename-0002`: files differ: missing ['documents/travel/quartz_ledger_2025.xlsx', 'documents/travel/quartz_manual_q3.xlsx', 'documents/travel/quartz_payslip_2025.jpg'], unexpected ['documents/travel/ledger_2025.xlsx', 'documents/travel/manual_q3.xlsx', 'documents/travel/payslip_2025.jpg'] (calls: none)
- `bulk_rename-0003`: files differ: missing ['downloads/travel/lantern_brochure_draft.png', 'downloads/travel/lantern_minutes_q1.png', 'downloads/travel/lantern_recipe_2025.pdf'], unexpected ['downloads/travel/brochure_draft.png', 'downloads/travel/minutes_q1.png', 'downloads/travel/recipe_2025.pdf'] (calls: none)
- `bulk_rename-0004`: files differ: missing ['documents/inbox/cobalt_brochure_2025.png', 'documents/inbox/cobalt_ledger_2024.png', 'documents/inbox/cobalt_newsletter_revised.pptx'], unexpected ['documents/inbox/brochure_2025.png', 'documents/inbox/ledger_2024.png', 'documents/inbox/newsletter_revised.pptx'] (calls: none)
- `bulk_rename-0005`: files differ: missing ['downloads/inbox/harbor_contract_signed.png', 'downloads/inbox/harbor_itinerary_q1.docx', 'downloads/inbox/harbor_manual_signed.pdf'], unexpected ['downloads/inbox/contract_signed.png', 'downloads/inbox/itinerary_q1.docx', 'downloads/inbox/manual_signed.pdf'] (calls: none)
- `bulk_rename-0006`: files differ: missing ['documents/receipts/maple_blueprint_final.pptx', 'documents/receipts/maple_blueprint_q2.pdf', 'documents/receipts/maple_recipe_q1.png'], unexpected ['documents/receipts/blueprint_final.pptx', 'documents/receipts/blueprint_q2.pdf', 'documents/receipts/recipe_q1.png'] (calls: none)
- `bulk_rename-0007`: files differ: missing ['downloads/shared/falcon_manual_march.docx', 'downloads/shared/falcon_newsletter_final.pdf', 'downloads/shared/falcon_survey_draft.xlsx'], unexpected ['downloads/shared/manual_march.docx', 'downloads/shared/newsletter_final.pdf', 'downloads/shared/survey_draft.xlsx'] (calls: none)
- `topic_then_read-0002`: turn 1: the answer lacks ['flowerpot'] (calls: none)
- `nothing_matches-0001`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\17752\146\Documents\scans\quartz_q3.txt → C:\work\interview prep\projects\alfred\runs\sb\17752\146\Desktop\quartz_q3.txt) (calls: search_by_meaning, move_file)
- `nothing_matches-0004`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\17752\149\Downloads\travel\falcon_old.txt → C:\work\interview prep\projects\alfred\runs\sb\17752\149\Desktop\falcon_old.txt) (calls: search_by_meaning, move_file)
