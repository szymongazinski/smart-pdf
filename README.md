# Smart PDF

Lokalny edytor PDF dla Windows, z interfejsem po polsku, OCR polskim i angielskim oraz edytowalnym formatem projektu.

![Edytor Smart PDF](assets/screenshots/editor.png)

## Instalacja

Pobierz **SmartPDF-Setup-0.1.0-x64.exe** z [Releases](https://github.com/szymongazinski/smart-pdf/releases).
Instalator działa bez uprawnień administratora. Dodaje program do menu Start, dzięki czemu
można znaleźć go w wyszukiwarce Windows. Pyta o skrót na pulpicie, dodanie do menu
**Otwórz za pomocą** dla PDF i powiązanie projektów `.smartpdf`.
Nie zmienia automatycznie domyślnej aplikacji dla PDF. W Windows można ją wybrać w ustawieniach aplikacji domyślnych.

Program i instalator nie mają jeszcze komercyjnego podpisu cyfrowego. Windows może wyświetlić ekran SmartScreen.
Nie jest wymagany Python ani osobna instalacja Tesseract. Modele OCR są zawarte w instalatorze.

## Funkcje

* Pióro z kolorami, grubością i kryciem; linia, okrąg/elipsa, trójkąt i prostokąt.
* Zaznaczanie tekstu i kopiowanie. Zakreślacz, podkreślenie i przekreślenie w różnych kolorach.
* Lokalny OCR Tesseract LSTM z modelami `tessdata_best`, domyślnie polski + angielski i 300 DPI.
  Automatyczny OCR można wyłączyć lub anulować. Wyniki są zachowywane w projekcie i eksportowane jako niewidoczna warstwa tekstowa.
  Można również ponownie rozpoznać zaznaczone skany, np. po poprawieniu ich obrotu.
* Pola tekstowe z formatowaniem fragmentów: czcionka, rozmiar, pogrubienie, kursywa, podkreślenie, kolor i wyrównanie.
  Przesuwanie, zmiana rozmiaru i dowolny obrót obiektów; Shift przy obrocie ustala krok 15°.
* Zmiana istniejącego tekstu: zaznacz tekst, wybierz **Zmień tekst**, wpisz nową treść.
  W projekcie oryginał jest zachowany. Eksport usuwa zastępowany tekst lub piksele skanu i dodaje nowy tekst.
* Margines z dowolnej strony, podana szerokość w mm i domyślne pole na notatki.
* Obracanie bieżącej strony, stron wybranych przez Ctrl+klik lub całego dokumentu.
* Małe podglądy stron w panelu bocznym, przestawianie przez przeciąganie i usuwanie stron.
* Cofanie/ponawianie, kopiowanie/wycinanie/wklejanie i powielanie obiektów.
* Wyszukiwanie tekstu, powiększanie, tryb odczytu i pełny ekran; paski i panele można chować z menu Widok.
* Kopie odzyskiwania co 30 s. Po przerwaniu procesu pojawiają się na ekranie startowym.

## Dwa sposoby zapisu

**Ctrl+S — projekt `.smartpdf`:** archiwum ZIP z oryginalnym PDF, wersjonowanym opisem stron,
obiektami, marginesami i wynikami OCR. Projekt jest samowystarczalny i można ponownie edytować jego obiekty.
Historia cofania dotyczy bieżącej sesji i nie jest zapisywana w pliku.

**Ctrl+E — zwykły PDF:** zachowuje oryginalne teksty i wektory, nanosi edytowane obiekty jako
treść strony i dodaje dostępne wyniki OCR. Pola Smart PDF nie są już osobnymi obiektami edytora.
Eksport PDF nie zastępuje zapisu projektu. Pliki są zapisywane atomowo, aby błąd zapisu nie uszkodził poprzedniej wersji.

## Skróty

| Skrót | Działanie |
|---|---|
| Ctrl+O / Ctrl+N | Otwórz / pusty dokument |
| Ctrl+S / Ctrl+Shift+S | Zapisz projekt / zapisz jako |
| Ctrl+E | Eksport PDF |
| Ctrl+Z / Ctrl+Y lub Ctrl+Shift+Z | Cofnij / ponów |
| Ctrl+C / Ctrl+X / Ctrl+V | Kopiuj / wytnij / wklej obiekty |
| Ctrl+D / Delete | Powiel / usuń obiekty |
| V / S / G | Obiekty / zaznacz tekst / przesuwanie widoku |
| P / T / H / U / L | Pióro / tekst / zakreślacz / podkreślenie / linia |
| Ctrl+F | Wyszukiwanie |
| Ctrl+PageUp / Ctrl+PageDown | Poprzednia / następna strona |
| Ctrl+kółko / Ctrl+0 | Zoom / dopasuj stronę |
| Ctrl+Shift+R / F11 | Tryb odczytu / pełny ekran |

Skróty obiektów i pojedyncze litery narzędzi działają, gdy aktywny jest obszar dokumentu.
Dwuklik na polu tekstowym otwiera edytor formatowania. Uchwyt w prawym dolnym rogu zmienia rozmiar,
a okrąg nad obiektem pozwala go obracać.
Shift podczas rysowania okręgu lub prostokąta ustala równe wymiary; przy linii kąt co 45°.

## OCR i prywatność

OCR używa lokalnego CPU, do dwóch wątków w osobnym procesie. Dokumenty nie są wysyłane do internetu.
Obrazy są renderowane w 200/300/400 DPI, z ograniczeniem pamięci do około 24 mln pikseli na stronę.
Automatycznie rozpoznawane są strony bez użytecznej warstwy tekstowej (mniej niż 20 znaków),
które zawierają obraz albo grafikę. Strony z istniejącą warstwą tekstu są pomijane.
OCR zależy od jakości skanu; małe, przekrzywione lub odręczne pismo może być rozpoznane błędnie.

Modele są pobierane wyłącznie podczas budowania przez `scripts/fetch_ocr.py` z ustalonego commitu
oficjalnego repozytorium Tesseract, z weryfikacją SHA256. `SMARTPDF_TESSDATA` pozwala wskazać inny katalog modeli.
Zmiana języków w ustawieniach dotyczy kolejnych rozpoznawanych stron.

## Zakres pierwszej wersji

To wersja **0.1.0**. Zmiana istniejącego tekstu zastępuje wybrany fragment nowym polem;
nie rekonstruuje składu całej strony i może użyć innej czcionki. Tło zastępowanego obszaru jest białe.
Tekst dłuższy niż pole wymaga powiększenia pola. Zaznaczanie działa na poziomie słów i linii;
skomplikowany układ wielokolumnowy może wymagać zaznaczania mniejszych fragmentów.

Istniejące adnotacje i formularze są podczas importu zamieniane na stałą treść wizualną.
Podpisy cyfrowe, interaktywność formularzy i hiperłącza nie są zachowywane w eksporcie.
Import PDF chronionego hasłem wymaga hasła; projekt i eksport są zapisywane bez szyfrowania.
Zastępowanie tekstu nie jest narzędziem do bezpiecznej redakcji całego dokumentu:
oryginał pozostaje w `.smartpdf`, a eksport nie usuwa automatycznie wszystkich metadanych i załączników.

## Uruchamianie ze źródeł

Python 3.11+; docelowo Windows 10/11 x64.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
python scripts/fetch_ocr.py
python -m smart_pdf
```

Można też podać ścieżkę: `python -m smart_pdf 'C:\Dokumenty\plik.pdf'`.

## Testy i budowanie

```powershell
python -m pytest -q
winget install --id JRSoftware.InnoSetup --exact
./scripts/build.ps1
```

Wyniki: `dist/SmartPDF/SmartPDF.exe` i `dist/installer/SmartPDF-Setup-0.1.0-x64.exe`.
Testy sprawdzają round-trip projektów, atomowy zapis, eksport tekstu Unicode,
geometrię stron i marginesów, zastępowanie tekstu, prawdziwy OCR, wektorowe kształty,
cofanie/ponawianie i podstawowe interakcje interfejsu.
Gotowy szablon GitHub Actions znajduje się w `scripts/github-actions-build.yml`.
Po skopiowaniu go do `.github/workflows/build.yml` testuje i buduje również tagi wydań.
Do dodania aktywnego workflow na GitHub potrzebne jest uprawnienie `workflow` tokenu.
Test samodzielnego EXE: `SmartPDF.exe --self-test 'C:\Temp\SmartPDF-test'`.
Tworzy wyłącznie własne dane testowe, sprawdza zapis i eksport i kończy działanie.

## Licencja

[AGPL-3.0-or-later](LICENSE). Zależności i ich licencje: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Kod źródłowy, skrypty budowania oraz wersje bibliotek są publiczne. Qt jest dołączony
jako wymienne biblioteki dynamiczne.
