# PL21 — uploader test (the public "bring your own firmware" page)

**What it is:** the public uploader (`build/site/public/uploader/index.html`) makes CTPlay from the official firmware
file you pick, on your computer, and sends it. This plan checks the page on a real Circuit Tracks: the file checks, the
tick boxes, the bootloader rule, the same-version warning, an install both ways, an abort and the recovery steps.
It needs no other part of the beta test. The marker PL21 is the working name (see `TEST.md`); read "PL21" as the beta
build.

> **If anything goes wrong** (a hang, the Circuit does not start, an install fails): unplug it, hold the power button
> 15–30 s, hold **Scales + Preset + Note** while you power on (bootloader mode), then send "Official 1.2.1" from this
> page. (With CTPlay running, Components reports the firmware as up to date and offers no install: TEST-components
> row 83.) Your projects, patches and samples stay on the SD card.

**Time:** about **30 min** (an estimate: 40 rows at about 30 s is 20 min; the five firmware installs add about 12 min).
Section A needs no Circuit Tracks and takes about 5 min. Each section says how it starts.

## Before you start
0. **PL21 installed** on the Circuit Tracks and running normally. (If not: `TEST.md` in this folder, "Before you
   start".) Back up your projects and the SD card first, as the page asks you to.
1. **Files at hand** (all on your computer):
   - the **official `.syx`**: download `circuittracks-firmware-4486.syx` from the link in the page's step 1;
   - the **`.bin`** made from it: from `slim/`, `../.venv/bin/python ../tools/ct_fw.py <the official .syx> -o official.bin`
     (pick another folder than the page's);
   - **a wrong file**: `slim/build/PL21/circuittracks-4486-PL21.syx` (CTPlay's own finished `.syx`; build it with
     `../.venv/bin/python -m slimbuild versions/PL21.toml` if it is missing) and a small text file named `notes.txt`.
2. **Build and open the page.** From `slim/`, in this order (the guide's build empties `build/site/`, so the page
   comes second):
   - `../.venv/bin/python -m slimbuild.guide`
   - `../.venv/bin/python -m slimbuild.uploader --public`
   - `cd build/site/public && python3 -m http.server 8000`, then open `http://localhost:8000/uploader/` in **Chrome or
     Edge**. Or use the hosted page, if it is up.
   - The build must print no error.
3. **One MIDI program at a time.** Close Components, CTCtrl, the link page and every other MIDI tab. **Chrome keeps a
   tab's port until you close the tab** (a refresh is not enough).
4. **Bootloader mode:** switch the Circuit Tracks off, hold **Scales + Preset + Note**, switch it on. The pads stay
   dark, the screen shows the bootloader. **Normal mode:** switch it off and on without holding anything.
5. **After every send,** the Circuit Tracks restarts and its MIDI ports go away. Wait until it has started, then press
   **Allow MIDI** again on the page, and **Identify the device**.
6. **Look at the Log** at the bottom of the page when a row says "Write down".

## Steps

### A. The page alone (no Circuit Tracks needed)
Start: **the page open, no file picked, MIDI not allowed.**

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Look at step 2's list and at step 2's text | The list holds **CTPlay 1.0 beta 1 (PL21)** and **Official 1.2.1 (Novation's firmware, unchanged)**, nothing else. The text under step 2 says "Pick the official firmware file first (step 1)." | |
| 2 | Look at step 4 | Send is grey (it cannot be pressed). Under the buttons: "Send needs: the official firmware file (step 1), MIDI ports (step 3), the backup box, the risk box." Both tick boxes show their full sentences | |
| 3 | Create a small text file named `notes.txt` (any words). In step 1, open the file picker. It shows only `.syx` and `.bin` files at first: switch its file type to **All files**, then pick `notes.txt` | Red: "notes.txt: This is not the official 1.2.1 (build 4486) firmware. Download the right file with the link above." Send stays grey | |
| 4 | Pick CTPlay's finished PL21 `.syx` (the wrong file) | Red: "circuittracks-4486-PL21.syx: This is not the official 1.2.1 (build 4486) firmware. Download the right file with the link above." Nothing more. Under step 2: "Pick the official firmware file first (step 1)." Send stays grey | |
| 5 | Pick the **official `.syx`** | Green: "...: This is the official 1.2.1 (build 4486) firmware." Under step 2: green "Ready: CTPlay 1.0 beta 1 (PL21). Its image and .syx match the published SHA-256 (N messages)." | |
| 6 | Pick the **`.bin`** instead | The same two green lines | |
| 7 | In step 2, choose **Official 1.2.1** | Green "Ready: Official 1.2.1. Its .syx matches the published SHA-256 (N messages)." **The risk box (the sentence about unofficial firmware) disappears.** Only the backup box is left | |
| 8 | Choose CTPlay 1.0 beta 1 (PL21) again | "Ready: CTPlay 1.0 beta 1 (PL21)..." again. The risk box is back | |
| 9 | Scroll to the end of the page | "If it goes wrong" with four numbered recovery steps and a link to the guide; the footer: not affiliated with Novation, MIT licence, based on CIRCUIT-HACKS-RC's uploader by Ghillermo | |
| 10 | (Optional, only in Safari) Open the same address there | Red: "This browser has no Web MIDI with SysEx. Use desktop Chrome or Edge." Allow MIDI is grey. (Firefox is not a test here: it has Web MIDI, and the page then shows "No MIDI access yet.") | |

### B. Identify, the boxes and the same version
Start: **PL21 running normally, USB connected, the page open in Chrome / Edge with the official `.syx` picked and
CTPlay 1.0 beta 1 (PL21) chosen.** Tick boxes clear.

| # | Do | Expect | Result |
|---|---|---|---|
| 11 | Press **Allow MIDI** | Green "MIDI access granted." The two port lists name the Circuit Tracks. Identify is no longer grey. (If another port is selected, pick the Circuit Tracks in both lists) | |
| 12 | Press **Identify the device** | Green: "Circuit Tracks running its firmware (build 4486). CTPlay PL21 is installed." Below, in orange: "PL21 is already installed. The Circuit Tracks would take this file and then keep PL21 without installing it again (same version)." | |
| 13 | Tick the backup box and the risk box. Look at Send | Send is **still grey**. Under it: "Send needs: bootloader mode, or the box in step 3." (The page sends only in bootloader mode.) | |
| 14 | Switch the Circuit Tracks off. Hold Scales + Preset + Note and switch it on (bootloader). Press **Allow MIDI**, then **Identify the device** | Green: "Circuit Tracks in bootloader mode (build 3556)." The orange same-version warning is **still there** (the page remembers PL21). Send is **active** (both boxes are still ticked from row 13) | |
| 15 | Untick the risk box | Send grey. "Send needs: the risk box." | |
| 16 | Untick the backup box too | "Send needs: the backup box, the risk box." | |
| 17 | Tick the backup box only. Choose **Official 1.2.1** in step 2 | The risk box is hidden. Send is **active** (Official needs only the backup box) | |
| 18 | Choose CTPlay 1.0 beta 1 (PL21) again | The risk box is back, **unticked**. Send grey, "Send needs: the risk box." | |
| 18b | Tick the risk box | Send is **active**; the hint under it is empty | |

### C. Send the same version
Start: **bootloader mode (row 14), CTPlay 1.0 beta 1 (PL21) chosen, the official `.syx` picked, both boxes ticked.**

| # | Do | Expect | Result |
|---|---|---|---|
| 19 | Press **Send**. Read the dialog. Press OK | The dialog: "Send CTPlay 1.0 beta 1 (PL21) to ..." and "Don't unplug the Circuit Tracks until it has finished." The progress bar starts to fill, "Sending…". Abort is active. The tick boxes and the file are locked | |
| 20 | Wait. (In bootloader mode the Circuit Tracks does not ask for Play: the page shows no Play prompt, and the Log goes from the send straight to the status) | The bar reaches the end. Abort turns grey once the bar is full (everything is sent). The Log shows "status 127: SUCCESS". The page says: "The Circuit Tracks received the file and restarts. It installs the file only if it is a different version from the one installed. When it runs normally again, press Allow MIDI and Identify the device to check." **It does not say "Installed"**. Orange: "The device is restarting. When it has started, press Allow MIDI." | |
| 21 | Wait until the Circuit Tracks has started (it may start in normal mode by itself). If it shows the bootloader, switch it off and on normally. Press **Allow MIDI**, then **Identify the device** | Green line "CTPlay PL21 is installed." The phase line turns **red**: "The Circuit Tracks still runs CTPlay PL21: that version was installed before, so the firmware was not changed." | |

### D. Official, then CTPlay from the `.bin`
Start: **PL21 running normally. Page still open (or reopened with the official `.syx` picked).**

| # | Do | Expect | Result |
|---|---|---|---|
| 22 | Restart in bootloader mode. Allow MIDI, Identify. Choose **Official 1.2.1**. Make sure the backup box is ticked (the risk box is hidden). Press Send, OK | Send is active (Official needs only the backup box). The dialog says "Send Official 1.2.1 to ..." | |
| 23 | Wait for the end (no Play prompt in bootloader mode) | "status 127: SUCCESS" and the "received ... restarts" text. No "Installed" | |
| 24 | Let it start normally. Allow MIDI on the page, then Identify | The page: "Circuit Tracks running its firmware (build 4486). No CTPlay reply: the official firmware or another build." The phase line is green: "No CTPlay answered: the official firmware or another firmware is running." | |
| 25 | Restart in bootloader mode. Allow MIDI, Identify. Pick the **`.bin`**. Choose CTPlay 1.0 beta 1 (PL21). Make sure both boxes are ticked. The orange warning is **not** shown (no CTPlay is installed). Press Send, OK | "Ready: CTPlay 1.0 beta 1 (PL21)..." then the transfer as in row 20 | |
| 26 | Let it start normally. Allow MIDI, Identify | The page: "CTPlay PL21 is installed." and a green phase line: "Installed: CTPlay 1.0 beta 1 (PL21)." | |

### E. An aborted send
Start: **PL21 running normally.**

| # | Do | Expect | Result |
|---|---|---|---|
| 27 | Restart in bootloader mode. Allow MIDI, Identify. Choose **Official 1.2.1**. Make sure the backup box is ticked. Press Send, OK. While the bar is filling ("Sending…", about halfway: the send takes about 18 s), press **Abort** | Orange: "Aborted. The Circuit Tracks drops the unfinished update and keeps its old firmware." Send and the boxes are usable again. Abort is grey | |
| 28 | Switch the Circuit Tracks off and on normally. Allow MIDI, Identify | The page says "CTPlay PL21 is installed." The old firmware is still there | |

### F. The recovery steps, and a send to the running firmware
Start: **PL21 running normally.**

| # | Do | Expect | Result |
|---|---|---|---|
| 29 | Do the page's "If it goes wrong" steps exactly: unplug, hold the power button 15–30 s, hold Scales + Preset + Note and switch on. Allow MIDI, Identify. Choose **Official 1.2.1**, make sure the backup box is ticked, Send, OK | The bootloader starts. Identify: "Circuit Tracks in bootloader mode". The send ends with "received ... restarts" | |
| 30 | Let it start. Allow MIDI, Identify | "No CTPlay reply..." and the green "No CTPlay answered..." line. **The recovery way back works** | |
| 31 | Now **with the Circuit Tracks running normally (stock)**: Allow MIDI, Identify. Pick the **official `.syx`**, choose CTPlay 1.0 beta 1 (PL21), make sure both boxes are ticked. Send stays grey with "bootloader mode, or the box in step 3". Tick **I know what I'm doing: send to the running firmware**. Press Send, OK. When the Circuit Tracks asks (white blinking), press **Play** | Send is now active. From the start the page says, in orange, "Starting… Press Play on the Circuit Tracks when it asks." (the running firmware asks for Play without telling the page; bootloader mode does not ask). After Play the bar fills. The end text adds: "It was sent to the running firmware: check it with Identify." | |
| 32 | Let it start. Allow MIDI, Identify | The device decides which. Installed: green "Installed: CTPlay 1.0 beta 1 (PL21)." Not installed: red "The Circuit Tracks still runs a firmware without CTPlay: the firmware was not changed." **Write down** which. The page must say what Identify finds, never "success" alone | |
| 33 | If row 32 did not install PL21: restart in bootloader mode, Allow MIDI, Identify, make sure both boxes are ticked, send PL21 as in row 25, then Identify. (The running-firmware box from row 31 is still ticked: in bootloader mode it changes nothing) | PL21 installed, green "Installed: ..." | |
| 34 | Allow MIDI, Identify | "CTPlay PL21 is installed.": the Circuit Tracks ends on PL21 | |
| 34b | **The same file to the running firmware** (added 2026-11-21). With PL21 running normally: reload the page, pick the official `.syx`, choose CTPlay 1.0 beta 1 (PL21), tick both boxes and the running-firmware box. Allow MIDI, Identify, Send, OK | At once, orange: "Starting… Press Play on the Circuit Tracks when it asks." The Circuit Tracks shows its update screen, then asks for Play (white blinking) | |
| 34c | Press **Play** on the Circuit Tracks | The bar fills. The Log: "status 127: SUCCESS (after 11116 of 11116 messages)", then the "received ... restarts" text, with "It was sent to the running firmware: check it with Identify." No "← device (not known to the page)" line. The Circuit Tracks restarts | |
| 34d | When it is ready: Allow MIDI, Identify | "CTPlay PL21 is installed." | |

### G. Windows with Components open (skip on other systems)
Start: **PL21 running normally. Close the page's tab.**

| # | Do | Expect | Result |
|---|---|---|---|
| 35 | Open the **Novation Components desktop app** (not a Chrome tab) and let it connect to the Circuit Tracks. Open the uploader in Chrome. Allow MIDI, Identify | The page cannot reach the port. **Write down** which red text shows: "Could not open the port: (a reason). Close Components, any DAW and other MIDI pages, then press Allow MIDI again." or "No reply. Check the ports and the cable." If Identify works anyway, **write that down** | |
| 36 | Quit the Components app and close the uploader tab. Open the uploader again. Allow MIDI, Identify | Identify works: "CTPlay PL21 is installed." | |

## Results

Date and time taken:  
Browser and system:  
Page address used:  

A: All steps passed  
B: All tests passed  
C: All tests passed  
D: All tests passed  
E: All tests passed  
F: F32 "Installed: CTPlay 1.0 beta 1 (PL21)." + "CTPlay PL21 is installed.". All tests passed  
G: G35 Identify works 

Anything the page said that a first-time user would not understand:  
