# Resources: what CTPlay has and uses

<!-- resources: PL22 -->
Figures for **PL22** (CTPlay 1.0 beta 2), from `firmware/PL22/manifest.json`. `tests/test_resources.py`
checks every row against that manifest: when a new build is published, update the marker above and the rows.

| Resource | Where | Size | Used by PL22 | Free |
|---|---|---|---|---|
| Flash | `0x0805CDE0–0x08080000` | 143,904 B | 40,776 B | 103,128 B |
| RAM: heap tail | `0x20044D68–0x20044E58` | 240 B | 120 B | 120 B |
| RAM: ITCM | `0x00000400–0x00004000` | 15,360 B | 3,048 B | 12,312 B |
| Saved | session record tail + 0 | 988 B | 118 B | 870 B |

- **Flash:** the code caves after stock's image, up to the bootloader's 0x70000 B limit.
- **Heap tail:** the end of stock's heap, which stock never allocates after boot. CTPlay lowers the heap limit to
  reserve it. This is the tight one. PL16 moved the CTCtrl link's last-sent image of the payload (81 B in PL15) to
  ITCM, so the tail went from 200 B used to 116 B: the link keeps 13 B there (the mailbox 12 B, the hello port 1 B;
  budget 16 B), the rest is the chord feature's and the count-in's run state. Every setting added since PL14 went to ITCM (PL15: the row-2 shape and voice
  leading 4 B, the previous chords 28 B, the recording fix's latch 32 B; PL16: `repeat_cfg` 2 B, `drum_page` 4 B, the
  note repeat engine 59 B; PL17: the drums' Pattern tools settings 28 B and their Undo 516 B; PL18: `chord_step` 1 B; PL19: pattern strum; PL20: trig conditions).
  PL17–PL20 left the tail as PL16 had it. PL21: the link's chunk queue (`ack`, `want`, the port: 4 B), 120 B used.
- **ITCM:** blocks 1–15 of the instruction RAM (block 0 is excluded: stock writes it at times). A feature gets it only
  by asking (`[budget] itcm`); CTPlay write-tests and zeroes its span at every power-on and stays off if the test fails.
  The link's image (118 B in PL20, 117 B in PL19, 116 B in PL18, 115 B in PL17, 87 B in PL16; budget 128 B) is here. PL17: the drums'
  Pattern tools settings 28 B, their Undo copies 4 × 128 B and where each came from 4 B. PL18: `chord_step` 1 B (the
  span's alignment took it: ITCM used stays 1,876 B). PL19 (+820 B): `chord_pstrum` 1 B; Played's queue 112 B
  (`pstrum_q` 96, `pstrum_beat` 12, `pstrum_gen` 4); a step entry's pending spills 260 B (`spill` 16 × 16 B, `entering` 4);
  recording a strum 444 B (the latch `prec` 192, `tickets` 128, `inflight` 8, the waiting ticket 12, `pstrum_roll` 32,
  `beat_tick` 4, mono record's `mono_past` 64, recfix's `recfix_picking` 4); the rest alignment. PL20 (+348 B): the
  saved mark `trig_mark` 1 B; Played's late-note start ticks 16 B (`pstrum_q.at`, 4 × 4); the passes' counts 134 B
  (`trig_count` 8 × 8 × 2 = 128, `trig_ms` 4, `trig_restart` 1, `trig_scene_wait` 1); playback 4 B (`trig_pre`,
  `trig_silent`, `trig_fill_hold`, `trig_fill_pass`); the row-4 latch 16 B (`trig_latch`); FILL 28 B (`trig_fill_arm`
  4, `trig_fill_ms` 16, `trig_fill_started` 4, `trig_fill_done` 4); the drum Write's Undo of the conditions 144 B
  (`drum_undo_cond` 4 × 36); the rest alignment. The mark is saved with the project; the rest is RAM only.
- **Saved (PL21, saved format 2; spec `specs/2026-11-10-saved-format-2-design.md`):** one block at the session
  record's tail + 0, a 12 B header (`CTPL`, format 2, layout ID, n, CRC-16, pending) and room for 988 B of payload
  (118 B used). A save keeps a newer build's bytes past this build's payload. The alpha blocks below are only read
  (a project from PL10–PL20), until 1.0.
- **Saved, PL10–PL20:** one logical payload (118 B in PL20, 117 B in PL19, 116 B in PL18, 115 B in PL17, 87 B in PL16, 81 B in PL15, 77 B in PL14) in two blocks
  (`features/saved/saved.c`, PL14). Block 1 is the 64 B block PL10-PL13 read (8 B header, the payload's first 56 B),
  always written full. Block 2 follows at + 832 (8 B header, up to 160 B: the payload from byte 56 on); its check
  covers block 1 too, so a re-save on PL13 or older drops only block 2's fields, and one on PL14–PL16 only the fields
  past its own payload (PL15's `chord_voice`; PL16's `repeat_cfg` at 81 and `drum_page` at 83; PL17's `drum_euclid`,
  `drum_rhythm`, `drum_accent` and `drum_seed` at 87–114; PL18's `chord_step` at 115; PL19's `chord_pstrum` at 116; PL20's `trig_mark` at 117, saved, not linked). A block 2 field past 160 B needs a decision first.
- **Not used by CTPlay:** the DSP (both cores), the settings record's tail, the SD card.
- **Stack:** hooks run on stock's task stacks; Main and UI keep at least 1.5 KB free in heavy use (SL00D). Each
  hook's own depth is in the manifest (`stack`, `hook_stack`). PL17: the CTCtrl link's budget is 560 B (`link_on_leds`
  560 B: its copies of the 115 B payload sit on the UI stack; PL16 448 B at 87 B), so the LED task is 576 B (PL16
  464 B). A pad press 476 B (PL16 468 B), a pad release 444 B (a drum Write uses 232 B of it), Main (`main_ms`, the
  repeat hits included) 416 B, a Note-view pad 348 B (PL17 308 B: PL18 made the chord's build a function of its own,
  `chord_build`, shared with step entry); the recorders' quantise refresh (`rec_quant`, a `mid` hook)
  152 B, its 64 B stub included. PL18's step entry: a chord written into a step (`step_add`) 348 B, the pad again on a
  held step (`note_pad_press`) 220 B; stock's store calls uncounted. The LED task and the link stay as PL17 (the
  116 B payload fits PL17's frames). PL19: Main (`main_ms`) 432 B (the heartbeat sends Played's late notes and moves
  recorded strum notes; `seq_note_on` / `seq_end_entry` are stock's, uncounted); the player's step (`seq_play_step`)
  136 B and its reset (`seq_end_all`) 120 B, both with the stub; the recorders' commits (`rec_off_commit` 200 B,
  `rec_pass_commit` 208 B, `mid` hooks); step entry grew with the roll (`step_add` 396 B, `note_pad_press` 316 B: the
  exact-roll test's roll on the stack); a Note-view pad release still 192 B with the Written spill
  (`rec_touch` stock's, uncounted); a Note-view pad 356 B; the LED task 592 B (`link_on_leds` 576 B, the 117 B payload's copies). Several small hooks grew 24 B (`rec_commit` 128 B, `sysex_in` 120 B): their worst
  case is the first call, which runs every feature's init, and `chord_init` is 48 B now (PL16 24 B: it calls the
  drums' settings init). PL20: Main and the LED task as PL19 (`main_ms` 432 B, `led_task` 592 B: the
  link's state is 118 B, byte 117 sent as 0); on Main a step's tick 0 (`player_tick`, a `mid` hook) 160 B, the pass
  end (`track_advance`) 152 B, stock's three probability tests (`prob_note`, `prob_drum`, `prob_drum_first`) 152 B,
  `seq_tick` 336 B (PL19 328 B); on the UI task the probability views' pads 120 B, the container's release
  (`cont_release`) 128 B, the expanded view's press / release 120 B, stock's edits 120 B (Duplicate, Clear step /
  pattern, copy 1-16 → 17-32, a hit off, the flip removal; paste 128 B, Mutate and the micro-step removal 152 B);
  `seq_place` 128 B (any task). Step entry and the page pads as PL19. PL21: the LED task 488 B (PL20 592 B: the link
  builds one 64 B chunk per frame, `link_on_leds` 472 B); a new UI hook, the end of a held step's preview
  (`preview_end`) 120 B; the saved block's load `saved_on_leds` 84 B, its save `session_save` 88 B.

**Not used yet:** the RAM above the heap, `0x20044E58–0x2004F000` (41,384 B), confirmed free on the device by `SL01D`
(2026-10-28, `firmware/SL01D/TEST.md`; `region.above_heap`). It gets a row of its own when a build uses it. What it
holds must carry a signature or be cleared at power-on.

Region details and their evidence: `stock/memory.toml`.
