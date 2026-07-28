# Bundled caption fonts

Every font here is under the SIL Open Font License 1.1, except Noto Color
Emoji, which is under the Apache License 2.0. Both licences permit bundling,
redistribution and commercial use, including inside a rendered video.

The fonts are committed to the repository rather than downloaded at run time,
so a render works with no network and produces the same frame every time.

| File | Family | Licence | Source |
|---|---|---|---|
| `Anton-Regular.ttf` | Anton | OFL 1.1 | github.com/google/fonts/tree/main/ofl/anton |
| `Bangers-Regular.ttf` | Bangers | OFL 1.1 | github.com/google/fonts/tree/main/ofl/bangers |
| `Montserrat-Black.ttf` | Montserrat Black (900) | OFL 1.1 | github.com/google/fonts/tree/main/ofl/montserrat |
| `Montserrat-Bold.ttf` | Montserrat Bold (700) | OFL 1.1 | github.com/google/fonts/tree/main/ofl/montserrat |
| `Nunito-Bold.ttf` | Nunito Bold | OFL 1.1 | github.com/google/fonts/tree/main/ofl/nunito |
| `Oswald-Bold.ttf` | Oswald Bold | OFL 1.1 | github.com/google/fonts/tree/main/ofl/oswald |
| `PlayfairDisplay-Bold.ttf` | Playfair Display Bold | OFL 1.1 | github.com/google/fonts/tree/main/ofl/playfairdisplay |
| `Roboto-Bold.ttf` | Roboto Bold | OFL 1.1 | github.com/google/fonts/tree/main/ofl/roboto |
| `Roboto-Regular.ttf` | Roboto | OFL 1.1 | github.com/google/fonts/tree/main/ofl/roboto |
| `RobotoMono-Regular.ttf` | Roboto Mono | OFL 1.1 | github.com/google/fonts/tree/main/ofl/robotomono |
| `NotoColorEmoji.ttf` | Noto Color Emoji | Apache 2.0 | github.com/googlefonts/noto-emoji |

## A note on the Montserrat and Roboto files

Google now ships these two families as variable fonts only. A variable font
falls back to its default weight, and for Montserrat that default is weight
100, which is far too thin to read over video. The files here were made by
pinning the variable font to a fixed weight with `fontTools.varLib.instancer`:

    Montserrat-Bold.ttf    wght=700
    Montserrat-Black.ttf   wght=900
    Roboto-Bold.ttf        wght=700, wdth=100
    Roboto-Regular.ttf     wght=400, wdth=100

They are still the same OFL licensed outlines, just instanced.

## Why these families

They are the ones short form creators actually use, and the licence lets us
ship them:

* **Montserrat Black** is the Hormozi caption face, all caps with a yellow
  highlight on the spoken word.
* **Anton** and **Oswald** are condensed, so a long word still fits across a
  1080 pixel frame without shrinking.
* **Bangers** is the free stand-in for the Komika Axis look used on
  entertainment and challenge content.
* **Roboto** and **Roboto Mono** cover the neutral and the terminal looks.
* **Playfair Display** and **Nunito** cover the authored and the friendly ends.
