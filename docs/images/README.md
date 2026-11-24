# User guide images

Screenshots for `docs/user-guide.md`, taken at **2x** (the guide page shows them at half their pixels; `playbuild.guide`
embeds them, so keep each under 60 KB: WebP).

`ctctrl-chord.webp`, `ctctrl-pads.webp`, `ctctrl-repeat.webp` (2026-10-25, CTCtrl 1.2.4, `dev` 62c4013 = the live
`main`): CTCtrl's dev server (`npx vite` in the CTCtrl repo), a 390 × 844 Chromium context at device scale 2, the
CTPlay state put straight into the store from the page (`import('/src/stores/midiStore.ts')` and
`import('/tests/ctplayFixtures.ts')` → `useMidiStore.setState({connected: true, ctplay: {...PL16_INFO, payload:
newProjectPayload(87)}, activeTrack})`), the values then set by clicking the panel (the clicks apply at once without a
device): Chord = Triad, bass Below, voice leading Close, strum Medium, then `ctplayHints: {'0:arp': true}`; Pads = the
same, after the pads button; Repeat = `activeTrack: 'drum1'`, 1/16, Accent beat. An element screenshot of the CTPlay
panel (`div[class^="_panel_"]` holding the marker), converted to WebP (quality 0.88) by the browser's canvas
(`toBlob('image/webp', 0.88)`). No device needed.

`ctctrl-hide.webp` (2026-10-19, CTCtrl `main` 440c207; unchanged in 1.2.4, checked 2026-10-25): Settings' DEVICE
section with Follow device track selection on, the Hide row outlined in `#f099ff`.
