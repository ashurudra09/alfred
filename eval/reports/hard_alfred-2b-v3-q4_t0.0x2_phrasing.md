# Hard multi-step suite: alfred-2b-v3-q4 (248 tasks)

2026-11-18T06:32:11, commit `a8bd4a7`

- **Pass rate: 145/248 (58.5%)**
- **Reliability over 2 trials per task (they differ by phrasing): pass^1 58.5%, pass^2 46.8%**
- 2 trial(s) per task at temperature 0.0, tool list 1.2; the task count includes every trial and leaves out the `new_capability` (semantic search) tasks, which have their own row; embedding model running
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 17.2 s

| Tag | Passed |
|---|---|
| act_on_list | 4/16 |
| all_except | 6/14 |
| ask_then_act | 10/14 |
| bulk_rename | 1/16 |
| compare_files | 14/16 |
| conditional_act | 8/16 |
| count_and_size | 14/14 |
| deadline_reminder | 14/16 |
| decline_then_continue | 8/14 |
| filtered_bulk | 14/14 |
| find_then_act | 5/14 |
| held_out | 41/80 |
| memory_then_act | 4/14 |
| notes_and_reminders | 10/14 |
| pick_extreme | 9/14 |
| read_then_compute | 14/14 |
| recover_empty | 0/14 |
| shared | 104/168 |
| two_part | 10/14 |

Failures:

- `find_then_act-0001`: files differ: missing ['downloads/payslip_q1.xlsx'], unexpected [] (calls: recall, search_files)
- `find_then_act-0003`: files differ: missing ['downloads/survey_2023.pdf'], unexpected ['desktop/scans/survey_2023.pdf'] (calls: recall, search_files)
- `find_then_act-0003`: files differ: missing ['downloads/survey_2023.pdf'], unexpected ['desktop/scans/survey_2023.pdf'] (calls: search_files)
- `find_then_act-0004`: files differ: missing ['desktop/warranty_2023.xlsx'], unexpected [] (calls: search_files)
- `find_then_act-0004`: files differ: missing ['desktop/warranty_2023.xlsx'], unexpected [] (calls: recall, search_files)
- `find_then_act-0005`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\2896\6\Documents\scans\brochure_q3.xlsx to the Recycle Bin (restorable)) (calls: search_files, move_to_recycle_bin)
- `find_then_act-0005`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\18360\6\Documents\scans\brochure_q3.xlsx to the Recycle Bin (restorable)) (calls: search_files, move_to_recycle_bin)
- `find_then_act-0006`: files differ: missing ['desktop/warranty_2023.pptx'], unexpected ['documents/receipts/warranty_2023.pptx'] (calls: recall)
- `find_then_act-0006`: files differ: missing ['desktop/warranty_2023.pptx'], unexpected ['documents/receipts/warranty_2023.pptx'] (calls: search_files)
- `pick_extreme-0000`: turn 1: the answer lacks [('manual_2023.png',)] (calls: search_files, move_to_recycle_bin)
- `pick_extreme-0000`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\18360\15\Desktop\archive\itinerary_q2.pdf to the Recycle Bin (restorable)) (calls: search_files, move_to_recycle_bin)
- `pick_extreme-0004`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\2896\19\Downloads\travel\ledger_draft.pptx → C:\work\interview prep\projects\alfred\runs\sb\2896\19\Documents\ledger_draft.pptx) (calls: search_files, move_file)
- `pick_extreme-0004`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\18360\19\Downloads\travel\ledger_draft.pptx → C:\work\interview prep\projects\alfred\runs\sb\18360\19\Documents\ledger_draft.pptx) (calls: search_files, move_file)
- `pick_extreme-0006`: files differ: missing [], unexpected ['desktop/inbox/contract_revised.png'] (calls: search_files)
- `all_except-0000`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\2896\22\Downloads\scans → C:\work\interview prep\projects\alfred\runs\sb\2896\22\Desktop\archive\scans) (calls: move_file)
- `all_except-0000`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\18360\22\Downloads\scans\lease_2024.zip → C:\work\interview prep\projects\alfred\runs\sb\18360\22\Desktop\archive\lease_2024.zip) (calls: list_directory, move_file)
- `all_except-0001`: files differ: missing ['downloads/clients/contract_june.jpg', 'downloads/clients/contract_june.pdf', 'downloads/clients/invoice_old.pptx'], unexpected ['documents/shared/contract_june.jpg', 'documents/shared/contract_june.pdf', 'documents/shared/invoice_old.pptx'] (calls: none)
- `all_except-0002`: turn 1: proposed a change that was not asked for (Move C:\work\interview prep\projects\alfred\runs\sb\2896\24\Desktop\receipts → C:\work\interview prep\projects\alfred\runs\sb\2896\24\Downloads\shared\receipts) (calls: move_file)
- `all_except-0003`: files differ: missing ['desktop/receipts/brochure_q2.pptx', 'desktop/receipts/invoice_signed.jpg', 'desktop/receipts/warranty_2023.pdf'], unexpected ['downloads/archive/brochure_q2.pptx', 'downloads/archive/invoice_signed.jpg', 'downloads/archive/warranty_2023.pdf'] (calls: none)
- `all_except-0004`: files differ: missing ['desktop/clients/manual_2024.xlsx', 'desktop/clients/manual_revised.pdf', 'desktop/clients/survey_revised.jpg'], unexpected ['documents/travel/manual_2024.xlsx', 'documents/travel/manual_revised.pdf', 'documents/travel/survey_revised.jpg'] (calls: none)
- `all_except-0005`: files differ: missing ['documents/coursework/minutes_q2.pdf', 'documents/coursework/permit_draft.jpg', 'documents/coursework/thesis_signed.pptx'], unexpected ['downloads/shared/minutes_q2.pdf', 'downloads/shared/permit_draft.jpg', 'downloads/shared/thesis_signed.pptx'] (calls: none)
- `all_except-0006`: files differ: missing ['desktop/keepsakes/contract_march.xlsx', 'desktop/keepsakes/recipe_2023.jpg', 'desktop/keepsakes/transcript_2025.pptx'], unexpected ['downloads/receipts/contract_march.xlsx', 'downloads/receipts/recipe_2023.jpg', 'downloads/receipts/transcript_2025.pptx'] (calls: none)
- `memory_then_act-0000`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\18360\36\Desktop\keepsakes\syllabus_october → C:\work\interview prep\projects\alfred\runs\sb\18360\36\Desktop\keepsakes\syllabus_october.zip) (calls: recall, zip_folder)
- `memory_then_act-0001`: turn 1: the answer lacks ['permit_signed.pdf', 'minutes_revised.jpg', 'manual_q2.png'] (calls: none)
- `memory_then_act-0002`: files differ: missing ['downloads/archive/recipe_q3/invoice_final.pdf'], unexpected ['documents/invoice_final.pdf'] (calls: move_file)
- `memory_then_act-0002`: files differ: missing ['downloads/archive/recipe_q3/invoice_final.pdf'], unexpected ['documents/invoice_final.pdf'] (calls: move_file)
- `memory_then_act-0003`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\2896\39\Documents\housing\recipe_2023 → C:\work\interview prep\projects\alfred\runs\sb\2896\39\Documents\housing\recipe_2023.zip) (calls: recall, zip_folder)
- `memory_then_act-0003`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: zip_folder)
- `memory_then_act-0004`: turn 1: the answer lacks ['thesis_q2.xlsx', 'invoice_2024.jpg', 'recipe_old.jpg'] (calls: none)
- `memory_then_act-0005`: files differ: missing ['downloads/receipts/lease_revised/permit_q3.png'], unexpected ['documents/permit_q3.png'] (calls: move_file)
- `memory_then_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: zip_folder)
- `memory_then_act-0006`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\18360\42\Documents\receipts\contract_q3 → C:\work\interview prep\projects\alfred\runs\sb\18360\42\Documents\receipts\contract_q3.zip) (calls: recall, zip_folder)
- `two_part-0001`: files differ: missing ['downloads/scans/transcript_q1.txt'], unexpected ['downloads/scans/transcript_october.txt'] (calls: read_file, rename_file)
- `two_part-0001`: files differ: missing ['downloads/scans/transcript_q1.txt'], unexpected ['downloads/scans/transcript_october.txt'] (calls: none)
- `two_part-0003`: files differ: missing ['desktop/archive/proposal_2024.txt'], unexpected ['desktop/archive/proposal_2025.txt'] (calls: none)
- `two_part-0005`: files differ: missing ['downloads/receipts/permit_october.txt'], unexpected ['downloads/receipts/permit_revised.txt'] (calls: none)
- `recover_empty-0000`: files differ: missing ['downloads/brochure_revised.txt'], unexpected ['documents/travel/brochure_revised.txt'] (calls: search_files)
- `recover_empty-0000`: files differ: missing ['downloads/brochure_revised.txt'], unexpected ['documents/travel/brochure_revised.txt'] (calls: search_files)
- `recover_empty-0001`: turn 1: the answer lacks ['recipe_2025.md'] (calls: search_files)
- `recover_empty-0001`: turn 1: the answer lacks ['recipe_2025.md'] (calls: search_files)
- `recover_empty-0002`: files differ: missing ['downloads/payslip_final.txt'], unexpected ['documents/archive/payslip_final.txt'] (calls: search_files)
- `recover_empty-0002`: files differ: missing ['downloads/payslip_final.txt'], unexpected ['documents/archive/payslip_final.txt'] (calls: search_files)
- `recover_empty-0003`: turn 1: the answer lacks ['ledger_2024.md'] (calls: search_files)
- `recover_empty-0003`: turn 1: the answer lacks ['ledger_2024.md'] (calls: search_files)
- `recover_empty-0004`: files differ: missing ['desktop/lease_june.txt'], unexpected ['downloads/shared/lease_june.txt'] (calls: search_files)
- `recover_empty-0004`: files differ: missing ['desktop/lease_june.txt'], unexpected ['downloads/shared/lease_june.txt'] (calls: search_files)
- `recover_empty-0005`: turn 1: the answer lacks ['syllabus_q3.txt'] (calls: search_files)
- `recover_empty-0005`: turn 1: the answer lacks ['syllabus_q3.txt'] (calls: search_files, search_files)
- `recover_empty-0006`: files differ: missing ['downloads/warranty_old.md'], unexpected ['desktop/shared/warranty_old.md'] (calls: search_files)
- `recover_empty-0006`: files differ: missing ['downloads/warranty_old.md'], unexpected ['desktop/shared/warranty_old.md'] (calls: search_files)
- `ask_then_act-0001`: files differ: missing [], unexpected ['desktop/travel/newsletter_q3.pdf'] (calls: move_to_recycle_bin, move_to_recycle_bin)
- `ask_then_act-0001`: files differ: missing [], unexpected ['desktop/travel/newsletter_q3.pdf'] (calls: move_to_recycle_bin, move_to_recycle_bin)
- `ask_then_act-0002`: turn 1: did not ask (calls: copy_file, search_files)
- `ask_then_act-0005`: turn 1: did not ask (calls: copy_file, copy_file)
- `decline_then_continue-0002`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: move_to_recycle_bin)
- `decline_then_continue-0002`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: none)
- `decline_then_continue-0004`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: none)
- `decline_then_continue-0004`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: move_to_recycle_bin)
- `decline_then_continue-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: move_to_recycle_bin)
- `decline_then_continue-0006`: turn 1: proposed a change that was not asked for (Zip C:\work\interview prep\projects\alfred\runs\sb\18360\70\Documents\shared → C:\work\interview prep\projects\alfred\runs\sb\18360\70\Documents\shared.zip) (calls: move_to_recycle_bin, zip_folder)
- `notes_and_reminders-0000`: notes: expected [('transcript gate', 'QUARTZ-9770')], made [] (calls: none)
- `notes_and_reminders-0002`: notes: expected [('contract gate', 'FALCON-7584')], made [] (calls: none)
- `notes_and_reminders-0004`: notes: expected [('minutes gate', 'SAFFRON-7911')], made [] (calls: none)
- `notes_and_reminders-0006`: notes: expected [('proposal gate', 'SAFFRON-6601')], made [] (calls: none)
- `compare_files-0002`: turn 1: the answer lacks [2288] (calls: read_file, read_file)
- `compare_files-0004`: turn 1: the answer lacks [1693] (calls: read_file, read_file)
- `act_on_list-0000`: files differ: missing ['downloads/scans/invoice_draft.jpg', 'downloads/scans/ledger_old.png', 'downloads/scans/permit_final.jpg'], unexpected ['documents/receipts/invoice_draft.jpg', 'documents/receipts/ledger_old.png', 'documents/receipts/permit_final.jpg'] (calls: read_file, move_file, move_file, move_file)
- `act_on_list-0001`: files differ: missing ['documents/keepsakes/contract_revised.xlsx', 'documents/keepsakes/minutes_signed.docx', 'documents/keepsakes/syllabus_march.pptx'], unexpected ['downloads/clients/contract_revised.xlsx', 'downloads/clients/minutes_signed.docx', 'downloads/clients/syllabus_march.pptx'] (calls: none)
- `act_on_list-0002`: files differ: missing ['desktop/scans/itinerary_signed.docx', 'desktop/scans/newsletter_old.xlsx', 'desktop/scans/thesis_draft.png'], unexpected ['documents/clients/itinerary_signed.docx', 'documents/clients/newsletter_old.xlsx', 'documents/clients/thesis_draft.png'] (calls: none)
- `act_on_list-0002`: files differ: missing ['desktop/scans/itinerary_signed.docx', 'desktop/scans/newsletter_old.xlsx', 'desktop/scans/thesis_draft.png'], unexpected ['documents/clients/itinerary_signed.docx', 'documents/clients/newsletter_old.xlsx', 'documents/clients/thesis_draft.png'] (calls: none)
- `act_on_list-0003`: files differ: missing ['downloads/clients/invoice_draft.pdf', 'downloads/clients/ledger_q2.png', 'downloads/clients/roadmap_2025.pptx'], unexpected ['desktop/scans/invoice_draft.pdf', 'desktop/scans/ledger_q2.png', 'desktop/scans/roadmap_2025.pptx'] (calls: none)
- `act_on_list-0003`: files differ: missing ['downloads/clients/invoice_draft.pdf', 'downloads/clients/ledger_q2.png', 'downloads/clients/roadmap_2025.pptx'], unexpected ['desktop/scans/invoice_draft.pdf', 'desktop/scans/ledger_q2.png', 'desktop/scans/roadmap_2025.pptx'] (calls: none)
- `act_on_list-0004`: files differ: missing ['desktop/coursework/invoice_q2.jpg', 'desktop/coursework/permit_october.xlsx', 'desktop/coursework/proposal_old.docx'], unexpected ['downloads/shared/invoice_q2.jpg', 'downloads/shared/permit_october.xlsx', 'downloads/shared/proposal_old.docx'] (calls: none)
- `act_on_list-0005`: files differ: missing ['documents/clients/manual_final.pptx', 'documents/clients/minutes_signed.pdf', 'documents/clients/roadmap_signed.docx'], unexpected ['downloads/housing/manual_final.pptx', 'downloads/housing/minutes_signed.pdf', 'downloads/housing/roadmap_signed.docx'] (calls: none)
- `act_on_list-0005`: files differ: missing ['documents/clients/manual_final.pptx', 'documents/clients/minutes_signed.pdf', 'documents/clients/roadmap_signed.docx'], unexpected ['downloads/housing/manual_final.pptx', 'downloads/housing/minutes_signed.pdf', 'downloads/housing/roadmap_signed.docx'] (calls: none)
- `act_on_list-0006`: files differ: missing ['documents/coursework/blueprint_june.pdf', 'documents/coursework/contract_revised.xlsx', 'documents/coursework/syllabus_2025.png'], unexpected ['desktop/housing/blueprint_june.pdf', 'desktop/housing/contract_revised.xlsx', 'desktop/housing/syllabus_2025.png'] (calls: none)
- `act_on_list-0006`: files differ: missing ['documents/coursework/blueprint_june.pdf', 'documents/coursework/contract_revised.xlsx', 'documents/coursework/syllabus_2025.png'], unexpected ['desktop/housing/blueprint_june.pdf', 'desktop/housing/contract_revised.xlsx', 'desktop/housing/syllabus_2025.png'] (calls: none)
- `act_on_list-0007`: files differ: missing ['documents/clients/brochure_march.pdf', 'documents/clients/invoice_june.jpg', 'documents/clients/itinerary_signed.xlsx'], unexpected ['downloads/keepsakes/brochure_march.pdf', 'downloads/keepsakes/invoice_june.jpg', 'downloads/keepsakes/itinerary_signed.xlsx'] (calls: none)
- `deadline_reminder-0000`: reminders: expected ['2026-01-11 09:00'], set [] (calls: read_file)
- `deadline_reminder-0001`: reminders: expected ['2026-10-11 08:00'], set [] (calls: read_file)
- `conditional_act-0000`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0000`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0002`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0002`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0004`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0004`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `conditional_act-0006`: files differ: missing ['desktop/*.zip'], unexpected [] (calls: search_files)
- `bulk_rename-0000`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\2896\117\Desktop\shared\permit_october.xlsx → quartz_2024.xlsx) (calls: list_directory, rename_file)
- `bulk_rename-0000`: files differ: missing ['desktop/shared/quartz_permit_october.xlsx', 'desktop/shared/quartz_recipe_2024.docx', 'desktop/shared/quartz_recipe_2024.jpg'], unexpected ['desktop/shared/permit_october.xlsx', 'desktop/shared/recipe_2024.docx', 'desktop/shared/recipe_2024.jpg'] (calls: none)
- `bulk_rename-0001`: files differ: missing ['documents/keepsakes/saffron_itinerary_final.png', 'documents/keepsakes/saffron_proposal_2025.docx', 'documents/keepsakes/saffron_transcript_2024.docx'], unexpected ['documents/keepsakes/itinerary_final.png', 'documents/keepsakes/proposal_2025.docx', 'documents/keepsakes/transcript_2024.docx'] (calls: none)
- `bulk_rename-0001`: files differ: missing ['documents/keepsakes/saffron_itinerary_final.png', 'documents/keepsakes/saffron_proposal_2025.docx', 'documents/keepsakes/saffron_transcript_2024.docx'], unexpected ['documents/keepsakes/itinerary_final.png', 'documents/keepsakes/proposal_2025.docx', 'documents/keepsakes/transcript_2024.docx'] (calls: none)
- `bulk_rename-0002`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\2896\119\Documents\travel\ledger_2025.xlsx → quartz_2025.xlsx) (calls: list_directory, rename_file)
- `bulk_rename-0002`: files differ: missing ['documents/travel/quartz_ledger_2025.xlsx', 'documents/travel/quartz_manual_q3.xlsx', 'documents/travel/quartz_payslip_2025.jpg'], unexpected ['documents/travel/ledger_2025.xlsx', 'documents/travel/manual_q3.xlsx', 'documents/travel/payslip_2025.jpg'] (calls: none)
- `bulk_rename-0003`: files differ: missing ['downloads/travel/lantern_brochure_draft.png', 'downloads/travel/lantern_minutes_q1.png', 'downloads/travel/lantern_recipe_2025.pdf'], unexpected ['downloads/travel/brochure_draft.png', 'downloads/travel/minutes_q1.png', 'downloads/travel/recipe_2025.pdf'] (calls: none)
- `bulk_rename-0003`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\18360\120\Downloads\travel\minutes_q1.png → lantern_q1.png) (calls: list_directory, rename_file, rename_file)
- `bulk_rename-0004`: files differ: missing ['documents/inbox/cobalt_brochure_2025.png', 'documents/inbox/cobalt_ledger_2024.png', 'documents/inbox/cobalt_newsletter_revised.pptx'], unexpected ['documents/inbox/brochure_2025.png', 'documents/inbox/ledger_2024.png', 'documents/inbox/newsletter_revised.pptx'] (calls: none)
- `bulk_rename-0004`: files differ: missing ['documents/inbox/cobalt_brochure_2025.png', 'documents/inbox/cobalt_ledger_2024.png', 'documents/inbox/cobalt_newsletter_revised.pptx'], unexpected ['documents/inbox/brochure_2025.png', 'documents/inbox/ledger_2024.png', 'documents/inbox/newsletter_revised.pptx'] (calls: none)
- `bulk_rename-0005`: files differ: missing ['downloads/inbox/harbor_contract_signed.png', 'downloads/inbox/harbor_itinerary_q1.docx', 'downloads/inbox/harbor_manual_signed.pdf'], unexpected ['downloads/inbox/contract_signed.png', 'downloads/inbox/itinerary_q1.docx', 'downloads/inbox/manual_signed.pdf'] (calls: none)
- `bulk_rename-0005`: turn 1: proposed a change that was not asked for (Rename C:\work\interview prep\projects\alfred\runs\sb\18360\122\Downloads\inbox\contract_signed.png → harbor_contract.png) (calls: list_directory, rename_file, rename_file, rename_file)
- `bulk_rename-0006`: files differ: missing ['documents/receipts/maple_blueprint_final.pptx', 'documents/receipts/maple_blueprint_q2.pdf', 'documents/receipts/maple_recipe_q1.png'], unexpected ['documents/receipts/blueprint_final.pptx', 'documents/receipts/blueprint_q2.pdf', 'documents/receipts/recipe_q1.png'] (calls: none)
- `bulk_rename-0007`: files differ: missing ['downloads/shared/falcon_newsletter_final.pdf', 'downloads/shared/falcon_survey_draft.xlsx'], unexpected ['downloads/shared/newsletter_final.pdf', 'downloads/shared/survey_draft.xlsx'] (calls: list_directory, rename_file, rename_file)
- `bulk_rename-0007`: files differ: missing ['downloads/shared/falcon_manual_march.docx', 'downloads/shared/falcon_newsletter_final.pdf', 'downloads/shared/falcon_survey_draft.xlsx'], unexpected ['downloads/shared/manual_march.docx', 'downloads/shared/newsletter_final.pdf', 'downloads/shared/survey_draft.xlsx'] (calls: none)
