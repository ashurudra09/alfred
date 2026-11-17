"""The single-turn unseen-tools set (track 4F, step F3 (i)): requests answered with Alfred's 26 tools plus the 10
held-out ones (eval/unseen/specs.py) in the tool list. Written by Claude, like the other test sets, and disclosed.

- held-out: a held-out tool is the right call (6-7 per tool, phrasing varied, a few Hinglish and typos);
- lookalike: a built-in tool is right although a held-out one sounds close (reminder vs to-do, calculate vs
  convertUnits, read_file vs countWords, ...);
- none_fits: neither list can do it, the answer is "cannot".

  uv run python -m eval.unseen.items      # writes eval/testsets/unseen.jsonl
  uv run python -m eval.run --set unseen --tools unseen --system ... --contracts 1.2
"""

import json
from pathlib import Path

from alfred.contracts.schemas import TestItem

PATH = {"file": "path", "first": "path", "second": "path"}


def item(id_, text, decision, calls=(), rules=None, tags=()):
    return TestItem(id=id_, messages=[{"role": "user", "content": text}], expected_decision=decision,
                    expected_calls=[{"name": n, "arguments": a} for n, a in calls], arg_rules=rules or {},
                    tags=list(tags)).model_dump(mode="json")


def call(id_, text, name, args, rules=None, tags=()):
    return item(id_, text, "tool_call", [(name, args)], {**PATH, "item": "text", **(rules or {})},
                ["held_out", *tags])


ITEMS = [
    # clipboard_get / clipboard_set
    call("clip-get-01", "what's on my clipboard right now?", "clipboard_get", {}),
    call("clip-get-02", "read me whatever I copied last", "clipboard_get", {}),
    call("clip-get-03", "paste the clipboard contents here so I can see them", "clipboard_get", {}),
    call("clip-get-04", "clipboard mein kya hai?", "clipboard_get", {}, tags=["hinglish"]),
    call("clip-set-01", "copy 'MEADOW-8687' to my clipboard", "clipboard_set", {"text": "MEADOW-8687"}),
    call("clip-set-02", "put my address on the clipboard: 14 Larkfield Road, Leeds", "clipboard_set",
         {"text": "14 Larkfield Road, Leeds"}, {"text": "text"}),
    call("clip-set-03", "copy this so I can paste it: https://example.com/invite/7731", "clipboard_set",
         {"text": "https://example.com/invite/7731"}),
    call("clip-set-04", "clipbord pe daal do: otter-285", "clipboard_set", {"text": "otter-285"}, tags=["hinglish", "typo"]),
    # convertUnits
    call("units-01", "how many km is 26.2 miles?", "convertUnits", {"value": 26.2, "from_unit": "mi", "to_unit": "km"}),
    call("units-02", "convert 72 fahrenheit to celsius", "convertUnits", {"value": 72, "from_unit": "F", "to_unit": "C"}),
    call("units-03", "what is 5 lbs in kilograms", "convertUnits", {"value": 5, "from_unit": "lb", "to_unit": "kg"}),
    call("units-04", "2 gallons in litres?", "convertUnits", {"value": 2, "from_unit": "gal", "to_unit": "l"}),
    call("units-05", "my height is 180 cm, what's that in feet", "convertUnits", {"value": 180, "from_unit": "cm", "to_unit": "ft"}),
    call("units-06", "conver 3 cups to ml", "convertUnits", {"value": 3, "from_unit": "cup", "to_unit": "ml"}, tags=["typo"]),
    call("units-07", "10 km kitne miles hote hain", "convertUnits", {"value": 10, "from_unit": "km", "to_unit": "mi"}, tags=["hinglish"]),
    # countWords
    call("words-01", "how many words are in Documents\\essay_final.txt?", "countWords", {"file": "Documents\\essay_final.txt"}),
    call("words-02", "word count of Desktop\\cover_letter.txt please", "countWords", {"file": "Desktop\\cover_letter.txt"}),
    call("words-03", "how long is Downloads\\notes.txt, in lines and characters? I don't need the text",
         "countWords", {"file": "Downloads\\notes.txt"}),
    call("words-04", "is my statement in Documents\\personal_statement.txt under 650 words?", "countWords",
         {"file": "Documents\\personal_statement.txt"}),
    call("words-05", "Documents\\thesis\\chapter2.md mein kitne words hain", "countWords",
         {"file": "Documents\\thesis\\chapter2.md"}, tags=["hinglish"]),
    call("words-06", "count teh words in Desktop\\speech.txt", "countWords", {"file": "Desktop\\speech.txt"}, tags=["typo"]),
    # hashFile
    call("hash-01", "give me the sha256 of Downloads\\ubuntu-24.04.iso", "hashFile", {"file": "Downloads\\ubuntu-24.04.iso"},
         {"algorithm": "any"}),
    call("hash-02", "I need the md5 checksum of Downloads\\setup.exe to check the download", "hashFile",
         {"file": "Downloads\\setup.exe", "algorithm": "md5"}),
    call("hash-03", "verify Downloads\\driver.zip: compute its checksum", "hashFile", {"file": "Downloads\\driver.zip"},
         {"algorithm": "any"}),
    call("hash-04", "sha1 hash of Documents\\contract_signed.pdf", "hashFile",
         {"file": "Documents\\contract_signed.pdf", "algorithm": "sha1"}),
    call("hash-05", "the website lists a checksum for this photo. what's the checksum of my Desktop\\photo.jpg?",
         "hashFile", {"file": "Desktop\\photo.jpg"}, {"algorithm": "any"}),
    call("hash-06", "Downloads\\installer.msi ka hash nikalo", "hashFile", {"file": "Downloads\\installer.msi"},
         {"algorithm": "any"}, tags=["hinglish"]),
    # files-differ
    call("diff-01", "what changed between Documents\\cv_old.txt and Documents\\cv_new.txt?", "files-differ",
         {"first": "Documents\\cv_old.txt", "second": "Documents\\cv_new.txt"}),
    call("diff-02", "compare Desktop\\notes_v1.md with Desktop\\notes_v2.md", "files-differ",
         {"first": "Desktop\\notes_v1.md", "second": "Desktop\\notes_v2.md"}),
    call("diff-03", "show me the lines that differ in Downloads\\config.ini vs Documents\\config.ini", "files-differ",
         {"first": "Downloads\\config.ini", "second": "Documents\\config.ini"}),
    call("diff-04", "did anything change between Documents\\draft.txt and Documents\\draft_final.txt", "files-differ",
         {"first": "Documents\\draft.txt", "second": "Documents\\draft_final.txt"}),
    call("diff-05", "Desktop\\a.txt aur Desktop\\b.txt mein kya farak hai", "files-differ",
         {"first": "Desktop\\a.txt", "second": "Desktop\\b.txt"}, tags=["hinglish"]),
    call("diff-06", "diff Documents\\list1.txt and Documents\\list2.txt", "files-differ",
         {"first": "Documents\\list1.txt", "second": "Documents\\list2.txt"}),
    # todo_add / todo_list / todo_done
    call("todo-add-01", "add 'renew passport' to my to-do list", "todo_add", {"item": "renew passport"}),
    call("todo-add-02", "put buy printer ink on my todo list, it's high priority", "todo_add",
         {"item": "buy printer ink", "priority": "high"}),
    call("todo-add-03", "to-do: submit the expense report, due 2026-10-30", "todo_add",
         {"item": "submit the expense report", "due": "2026-10-30"}),
    call("todo-add-04", "add call the plumber to my tasks, low priority", "todo_add",
         {"item": "call the plumber", "priority": "low"}),
    call("todo-add-05", "todo list mein daal do: gym membership cancel karna", "todo_add",
         {"item": "gym membership cancel karna"}, tags=["hinglish"]),
    call("todo-list-01", "what's on my to-do list?", "todo_list", {}, {"show": "any"}),
    call("todo-list-02", "show me the to-dos I've already finished", "todo_list", {"show": "done"}),
    call("todo-list-03", "list every to-do item, done or not", "todo_list", {"show": "all"}),
    call("todo-list-04", "which tasks are still open?", "todo_list", {}, {"show": "any"}),
    call("todo-done-01", "mark to-do 3 as done", "todo_done", {"number": 3}),
    call("todo-done-02", "I finished item 1 on my todo list", "todo_done", {"number": 1}),
    call("todo-done-03", "tick off number 2 on the to-do list", "todo_done", {"number": 2}),
    call("todo-done-04", "todo 4 ho gaya, done mark karo", "todo_done", {"number": 4}, tags=["hinglish"]),
    # colorConvert
    call("color-01", "what's #1e90ff in rgb?", "colorConvert", {"color": "#1e90ff", "to": "rgb"}),
    call("color-02", "convert rgb(255, 99, 71) to hex", "colorConvert", {"color": "rgb(255, 99, 71)", "to": "hex"}),
    call("color-03", "give me the HSL for #ff8800", "colorConvert", {"color": "#ff8800", "to": "hsl"}),
    call("color-04", "hex code for rgb(0, 128, 0)?", "colorConvert", {"color": "rgb(0, 128, 0)", "to": "hex"}),
    call("color-05", "#333333 ko rgb mein badlo", "colorConvert", {"color": "#333333", "to": "rgb"}, tags=["hinglish"]),
    call("color-06", "covnert hsl(210, 100%, 56%) to hex", "colorConvert", {"color": "hsl(210, 100%, 56%)", "to": "hex"},
         tags=["typo"]),
    call("color-07", "I have the colour rgb(46, 139, 87); what's its hex code?", "colorConvert",
         {"color": "rgb(46, 139, 87)", "to": "hex"}),
    call("clip-get-05", "did my last copy work? show me what's on the clipboard", "clipboard_get", {}),
    call("clip-set-05", "put the text 'Meeting moved to 3pm' on the clipboard", "clipboard_set",
         {"text": "Meeting moved to 3pm"}),
    call("units-08", "the recipe says 250 g of flour, how many ounces is that", "convertUnits",
         {"value": 250, "from_unit": "g", "to_unit": "oz"}),
    call("words-07", "roughly how many characters is Documents\\bio.txt? I need it under 1000", "countWords",
         {"file": "Documents\\bio.txt"}),
    call("hash-07", "compute an md5 for Documents\\backup.zip", "hashFile", {"file": "Documents\\backup.zip", "algorithm": "md5"}),
    call("diff-07", "has Documents\\budget_v2.csv changed from Documents\\budget_v1.csv? list the differences", "files-differ",
         {"first": "Documents\\budget_v1.csv", "second": "Documents\\budget_v2.csv"}),
    call("todo-add-06", "add 'book dentist appointment' to my to-dos, due 2026-11-02, normal priority", "todo_add",
         {"item": "book dentist appointment", "due": "2026-11-02"}, {"priority": "any"}),
    call("todo-done-05", "the second item on my to-do list is done", "todo_done", {"number": 2}),
]

LOOKALIKE = [  # a built-in tool is right
    ("look-01", "remind me at 5pm today to call the bank", "set_reminder",
     {"text": "call the bank", "time": "today 17:00"}, {"text": "text", "time": "time"}),
    ("look-02", "what's 18% of 2450?", "calculate", {"expression": "2450 * 18 / 100"}, {}),
    ("look-04", "read me Desktop\\speech.txt", "read_file", {"path": "Desktop\\speech.txt"}, {"max_chars": "any"}),
    ("look-05", "which file in Documents mentions 'quarterly targets'?", "search_file_contents",
     {"text": "quarterly targets", "folder": "Documents"}, {}),
    ("look-06", "save a note called 'parking' with the text 'Level 3, bay 42'", "create_note",
     {"title": "parking", "content": "Level 3, bay 42"}, {"content": "text"}),
    ("look-07", "remember that my bike shop is Wheelworks on Lindqvist Road", "remember",
     {"fact": "my bike shop is Wheelworks on Lindqvist Road"}, {"fact": "text"}),
    ("look-08", "what reminders do I have coming up?", "list_reminders", {}, {}),
    ("look-09", "add 2.5 GB and 700 MB", "calculate", {"expression": "2.5 GB + 700 MB"}, {}),
    ("look-10", "copy Desktop\\photo.jpg to Documents", "copy_file",
     {"source": "Desktop\\photo.jpg", "destination": "Documents"}, {}),
    ("look-11", "make a note 'groceries' listing milk, eggs and bread", "create_note",
     {"title": "groceries", "content": "milk, eggs and bread"}, {"content": "text"}),
    ("look-12", "what's 3 times 1,450 plus 200?", "calculate", {"expression": "3 * 1450 + 200"}, {}),
]

NONE_FITS = [
    "convert Documents\\report.docx to a PDF",
    "send Desktop\\photo.jpg to my sister on WhatsApp",
    "what's the exchange rate from dollars to rupees today?",
    "translate Documents\\letter.txt into French",
    "play my workout playlist",
    "turn the screen brightness down",
    "share my to-do list with Priya",
    "scan the document in the printer",
]

ALL = ITEMS + [item(i, t, "tool_call", [(n, a)], r, ["lookalike"]) for i, t, n, a, r in LOOKALIKE] + \
      [item(f"none-{k:02d}", t, "cannot", tags=["none_fits"]) for k, t in enumerate(NONE_FITS, 1)]

if __name__ == "__main__":
    out = Path(__file__).parents[1] / "testsets" / "unseen.jsonl"
    out.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ALL), encoding="utf-8")
    print(f"{len(ALL)} items -> {out}")
