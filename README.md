# English Phrases in Chunks — Work & Life

A list of English phrases to memorize as whole chunks, for work and daily life, with formulas for building sentences and daily practice of simple and perfect forms. Spanish is used only for the meanings.

Live page: https://danher2.github.io/english-page/

## Files

- `frases.md`: the content (source of truth). Edit this file.
- `build.py`: generates `index.html` from `frases.md`.
- `index.html`: the page GitHub Pages serves. Don't edit it by hand.

## Updating the page

```
python build.py
git add . && git commit -m "Update phrases" && git push
```

GitHub Pages refreshes within a minute or two.

## Page features

- **Search** across English and Spanish (press `/` to focus it).
- **Hide English / Hide Spanish** to quiz yourself; tap a hidden phrase to reveal it.
- **Listen** to any phrase with the speaker button (uses your device's English voice).
- Contents sidebar (a menu on mobile), dark mode, and a back-to-top button.
