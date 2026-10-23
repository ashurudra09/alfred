"""What each tool's result text looks like. The teacher writes fake results in this style, and the Phase 6 tools
return the same style, so training data and real use match. `{U}` is the example's username.
"""

RESULTS = {
    "search_files": "3 files:\nC:\\Users\\{U}\\Downloads\\attention_transformer.pdf (2.1 MB, modified 2026-10-15)\n"
                    "C:\\Users\\{U}\\Downloads\\transformer_notes.pdf (310 KB, modified 2026-09-02)\n...",
    "search_file_contents": "2 files:\nC:\\Users\\{U}\\Documents\\ml\\lora.md: \"...LoRA adds low-rank adapters...\"\n"
                            "C:\\Users\\{U}\\Documents\\notes.txt: \"...try LoRA r=16...\"",
    "list_directory": "C:\\Users\\{U}\\Downloads (5 items):\nphotos\\ (folder)\nlecture1.pdf (1.2 MB)\nsetup.exe (88 MB)\n...",
    "read_file": "C:\\Users\\{U}\\Documents\\notes.txt (1,204 chars):\nWeek 3 notes. LoRA adds low-rank adapters...",
    "disk_usage": "C:\\ 476 GB total, 18 GB free.\nLargest:\nC:\\Users\\{U}\\Videos 120 GB\nC:\\Users\\{U}\\AppData 96 GB\n...",
    "move_file": "Moved C:\\Users\\{U}\\Downloads\\resume.pdf to C:\\Users\\{U}\\Documents\\resume.pdf. Undo: /undo",
    "rename_file": "Renamed C:\\Users\\{U}\\Documents\\cv.pdf to cv_2026.pdf. Undo: /undo",
    "copy_file": "Copied C:\\Users\\{U}\\Documents\\thesis.docx to D:\\backup\\thesis.docx. Undo: /undo",
    "zip_folder": "Created C:\\Users\\{U}\\Documents\\resume.zip (4 files, 1.8 MB). Undo: /undo",
    "organize_folder": "Moved 14 files in C:\\Users\\{U}\\Downloads: 6 to PDFs\\, 5 to Images\\, 3 to Installers\\. "
                       "Undo: /undo",
    "move_to_recycle_bin": "Moved C:\\Users\\{U}\\Desktop\\temp.txt to the Recycle Bin. Undo: /undo",
    "open_path": "Opened C:\\Users\\{U}\\Documents\\budget.xlsx in its default app.",
    "open_app": "Launched Spotify.",
    "system_info": "CPU: Intel Core i5-1235U (10 cores), 23% busy. RAM: 7.1 of 15.7 GB used. "
                   "Battery: 64%, charging. Windows 11 Home 24H2.",
    "top_processes": "Top 5 by CPU:\nchrome.exe 18% CPU, 1.9 GB\nCode.exe 9% CPU, 820 MB\n...",
    "network_status": "Online. Wi-Fi: HomeNet_5G (signal 82%). Local IP: 192.168.1.23.",  # wired: "Online. Wired: Ethernet. Local IP: ..."
    "port_in_use": "Port 3000: node.exe (PID 18244).",  # or "Nothing is listening on port 3000."
    "git_status": "Branch main, 2 ahead / 0 behind origin/main.\nChanged: M src/app.py, ?? notes.md",
    "create_note": "Saved note 'Groceries' (note 12).",
    "search_notes": "2 notes:\n1. Interview prep (2026-10-21): revise DPO and GRPO\n2. Ideas (2026-10-02): CLI for alfred",
    "set_reminder": "Reminder set for 2026-10-23 09:00: call mom (reminder 4).",
    "list_reminders": "2 upcoming:\n1. 2026-10-23 09:00 call mom\n2. 2026-10-25 11:00 pay electricity bill",
    "remember": "Saved memory 7: Resume folder is D:\\docs\\resume.",
    "recall": "1. Resume folder is D:\\docs\\resume (saved 2026-10-01)\n2. ...",  # or "No matching memories."
    "calculate": "6299.82",
}
DECLINED = "The user declined this change. Nothing was changed."
