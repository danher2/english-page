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
- **Dictionary** (button in the toolbar, or press `d`): type an English word or phrase and get the Spanish meaning, an English explanation, synonyms, examples, the phonetic spelling, and audio (normal, slow, and a real recording when one exists). It also lists the phrases from your own list that use that word. Switch to **ES → EN** to search a Spanish word. On a computer, double-click any word on the page to look it up. Links like `.../#dict=deadline` open the dictionary on that word.

## Dictionary data

The dictionary runs in the browser with free services, no API keys and no server:

- [Free Dictionary API](https://dictionaryapi.dev/): English definitions, examples, phonetics, and recordings. Mostly single words; many phrases and idioms aren't covered.
- [Datamuse](https://www.datamuse.com/api/): synonyms and related words.
- [MyMemory](https://mymemory.translated.net/doc/spec.php): Spanish translations. The free tier allows about 5,000 characters a day per device, which is plenty for personal use.
- Audio uses your device's English voice (Web Speech API), like the rest of the page.
