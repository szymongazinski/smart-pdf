# Smart PDF

Lokalny edytor PDF dla Windows, z interfejsem po polsku, OCR polskim i angielskim oraz edytowalnym formatem projektu.

![Edytor Smart PDF](assets/screenshots/editor.png)

## Instalacja

Pobierz **SmartPDF-Setup-0.3.0-x64.exe** z [Releases](https://github.com/szymongazinski/smart-pdf/releases).
Instalator działa bez uprawnień administratora. Dodaje program do menu Start, dzięki czemu
można znaleźć go w wyszukiwarce Windows. Pyta o skrót na pulpicie, dodanie do menu
**Otwórz za pomocą** dla PDF i powiązanie projektów `.smartpdf`.
Nie zmienia automatycznie domyślnej aplikacji dla PDF. W Windows można ją wybrać w ustawieniach aplikacji domyślnych.

Program i instalator nie mają jeszcze komercyjnego podpisu cyfrowego. Windows może wyświetlić ekran SmartScreen.
Nie jest wymagany Python ani osobna instalacja Tesseract. Modele OCR są zawarte w instalatorze.
Instalator pozwala wybrać obliczenia GPU/CPU, języki i jakość OCR. Domyślnie:
GPU jeśli dostępne, polski + angielski, 300 DPI. Ustawienia są dostępne także w menu **OCR**.

## Aktualizacja istniejącej instalacji

Możesz też uruchomić **SmartPDF-Update-0.3.0-x64.exe** z tego samego wydania,
również jeśli masz wersję 0.1.0 bez przycisku sprawdzania aktualizacji.
Aktualizator znajduje istniejącą instalację, podmienia pliki i zachowuje ustawienia,
projekty oraz wybrane skróty. Nie trzeba odinstalowywać programu ani przechodzić ponownie
przez wybór folderu i skrótów. Przed aktualizacją zapisz pracę i zamknij Smart PDF.
Od wersji 0.2.0 użyj przycisku **Sprawdź aktualizacje** albo menu **Pomoc**.
Program sprawdza GitHub dopiero na kliknięcie i weryfikuje SHA256 przed uruchomieniem aktualizatora.
Przy pierwszym bezpośrednim uruchomieniu aktualizatora do 0.3.0 można skonfigurować OCR.
Aktualizacja z poziomu programu wybiera GPU, jeśli dostępne, i zachowuje języki oraz jakość;
wybór obliczeń można potem zmienić w menu **OCR → Ustawienia OCR…**.
Kolejne aktualizacje zachowują ustawienia.

## OCR z menu pliku PDF

Kliknij PDF prawym przyciskiem i wybierz **Smart PDF — wykonaj OCR**.
W Windows 11 polecenie znajduje się w **Pokaż więcej opcji** (lub Shift+F10).
Otwiera się osobne okno postępu, bez uruchamiania edytora. Po ukończeniu PDF zostaje
podmieniony w tym samym miejscu. Program zachowuje oryginalne obrazy, wektory,
rozmiary i obroty stron, linki, adnotacje, formularze, metadane i załączniki.
Dodaje niewidoczną, przeszukiwalną warstwę tekstową. Strony z istniejącym tekstem pomija.
Dokument z hasłem wymaga hasła i pozostaje zaszyfrowany.

Oryginał jest podmieniany dopiero po przygotowaniu i sprawdzeniu całego wyniku.
Anulowanie, błąd lub wykrycie równoczesnej zmiany pliku pozostawia PDF bez podmiany.
Lokalna kopia oryginału jest zachowywana w danych aplikacji, w folderze `OCR backups`;
okno wyniku udostępnia przycisk otwierający tę kopię. Podmiana treści unieważnia istniejący podpis cyfrowy.

## Funkcje

* Pióro z kolorami, grubością i kryciem; linia, okrąg/elipsa, trójkąt i prostokąt.
* Zaznaczanie tekstu i kopiowanie. Zakreślacz, podkreślenie i przekreślenie w różnych kolorach.
* Lokalny OCR PP-OCRv5: dokładny model wykrywania tekstu i rozpoznawanie alfabetu łacińskiego,
  domyślnie polski + angielski i 300 DPI. GPU przez DirectML lub CPU;
  mniej pewne linie dodatkowo rozpoznaje Tesseract LSTM z modelami `tessdata_best`.
  OCR jest domyślnie wyłączony; przycisk **OCR** uruchamia rozpoznawanie. Tryb automatyczny można włączyć w menu OCR na bieżącą sesję.
  Wyniki są zachowywane w projekcie i eksportowane jako niewidoczna warstwa tekstowa.
  Można również ponownie rozpoznać zaznaczone skany, np. po poprawieniu ich obrotu.
* Pola tekstowe z formatowaniem fragmentów: czcionka, rozmiar, pogrubienie, kursywa, podkreślenie, kolor i wyrównanie.
  Pisanie bezpośrednio na PDF po jednym kliknięciu, również w trybie zaznaczania tekstu.
  Przesuwanie za ramkę, zmiana rozmiaru i dowolny obrót obiektów; Shift przy obrocie ustala krok 15°.
* Przycisk **Margines** natychmiast dodaje prawy margines i puste pole na notatki; menu strzałki udostępnia lewy margines.
  Każda strona może mieć po jednym marginesie z lewej i z prawej. Ponowne kliknięcie otwiera istniejące notatki.
  Suwak szerokości zmienia margines i pole na żywo.
* Suwak grubości zmienia rysowanie i zaznaczone kształty na żywo; jeden ruch suwaka to jedna operacja cofania.
* Cały dokument przewijany pionowo. Ostre fragmenty podglądu są renderowane do aktualnego zoomu i skali ekranu.
  Pamięć podręczna rastrów jest ograniczona do 64 MB; jakość eksportu pochodzi z oryginalnego PDF, nie z podglądu.
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
Kliknij pole tekstowe, aby pisać. Formatowanie jest w panelu obok. Escape kończy pisanie.
Podczas pisania Ctrl+Z/Y i Ctrl+C/X/V dotyczą tekstu w polu; Ctrl+B/I/U zmienia formatowanie.
Uchwyt w prawym dolnym rogu zmienia rozmiar,
a okrąg nad obiektem pozwala go obracać.
Shift podczas rysowania okręgu lub prostokąta ustala równe wymiary; przy linii kąt co 45°.

## OCR i prywatność

OCR działa w osobnym procesie. Zalecany tryb używa GPU przez ONNX Runtime DirectML,
jeśli karta i sterownik to obsługują; w przeciwnym razie przechodzi na CPU.
Można też wybrać wyłącznie CPU albo klasyczny Tesseract LSTM. Renderowanie PDF,
przygotowanie obrazu, dodatkowe rozpoznawanie mniej pewnych linii i zapis korzystają z CPU.
Przyspieszenie GPU sprawdzono na NVIDIA RTX 4070 Ti z użyciem profilu wykonanych operacji.
Dokumenty nie są wysyłane do internetu. Wszystkie modele są dołączone do instalatora.
Obrazy są renderowane w 200/300/400 DPI, z ograniczeniem pamięci do około 24 mln pikseli na stronę.
Automatycznie rozpoznawane są strony bez użytecznej warstwy tekstowej (mniej niż 20 znaków),
które zawierają obraz albo grafikę. Strony z istniejącą warstwą tekstu są pomijane.
OCR zależy od jakości skanu; małe, przekrzywione lub odręczne pismo może być rozpoznane błędnie.

Modele są pobierane wyłącznie podczas budowania przez `scripts/fetch_ocr.py` i
`scripts/fetch_gpu_ocr.py`, z weryfikacją przypiętych sum SHA256.
Manifesty: `assets/ocr-models.json` i `assets/ppocr-models.json`.
`SMARTPDF_TESSDATA` pozwala wskazać inny katalog modeli Tesseract.
Zmiana języków w ustawieniach dotyczy kolejnych rozpoznawanych stron.

## Zakres pierwszej wersji

To wersja **0.3.0**. Zawiera OCR z menu pliku PDF, przyspieszenie GPU oraz poprawkę
znikających cienkich kresek liter w podglądzie przy skalowaniu.
Opcja zmiany oryginalnego tekstu PDF została usunięta.
Starsze projekty z takimi obiektami nadal się otwierają i eksportują.
Zaznaczanie działa na poziomie słów i linii, w obrębie jednej strony;
skomplikowany układ wielokolumnowy może wymagać zaznaczania mniejszych fragmentów.

Istniejące adnotacje i formularze są podczas importu zamieniane na stałą treść wizualną.
Podpisy cyfrowe, interaktywność formularzy i hiperłącza nie są zachowywane w eksporcie.
Import PDF chronionego hasłem wymaga hasła; projekt i eksport są zapisywane bez szyfrowania.
Format projektu zachowuje oryginał, a eksport nie usuwa automatycznie wszystkich metadanych i załączników.

## Uruchamianie ze źródeł

Python 3.12+; docelowo Windows 10/11 x64. GPU wymaga karty zgodnej z DirectML i sterownika DirectX 12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
python scripts/fetch_ocr.py
python scripts/fetch_gpu_ocr.py
python -m smart_pdf
```

Można też podać ścieżkę: `python -m smart_pdf 'C:\Dokumenty\plik.pdf'`.

## Testy i budowanie

```powershell
python -m pytest -q
winget install --id JRSoftware.InnoSetup --exact
./scripts/build.ps1
```

Wyniki: `dist/SmartPDF/SmartPDF.exe`, `dist/installer/SmartPDF-Setup-0.3.0-x64.exe`
oraz `dist/installer/SmartPDF-Update-0.3.0-x64.exe`.
Testy sprawdzają round-trip projektów, atomowy zapis, eksport tekstu Unicode,
geometrię stron i marginesów, zastępowanie tekstu, prawdziwy OCR, wektorowe kształty,
cofanie/ponawianie, pisanie na stronie, suwaki, ciągłe przewijanie, zachowanie cienkich
kresek w obrazie przy różnych powiększeniach i obrotach, ostrość kafelków
oraz weryfikację pobranych aktualizacji. Testy OCR z menu pliku porównują obraz stron
piksel po pikselu, sprawdzają obroty i przycięcia, polskie znaki, zachowanie linków,
adnotacji, metadanych, załączników i hasła, podmianę z kopią oraz anulowanie i błędy.
Gotowy szablon GitHub Actions znajduje się w `scripts/github-actions-build.yml`.
Po skopiowaniu go do `.github/workflows/build.yml` testuje i buduje również tagi wydań.
Do dodania aktywnego workflow na GitHub potrzebne jest uprawnienie `workflow` tokenu.
Test samodzielnego EXE: `SmartPDF.exe --self-test 'C:\Temp\SmartPDF-test'`.
Tworzy wyłącznie własne dane testowe, sprawdza zapis i eksport i kończy działanie.
Opcjonalny trzeci argument ze ścieżką do lokalnego PDF dodaje zrzuty jego podglądu
przy 125%, 175%, 210% i 300%, zapisane wyłącznie w podanym katalogu testowym.
Test OCR z menu pliku w gotowym EXE: `SmartPDF.exe --self-test-ocr 'C:\Temp\SmartPDF-OCR-test'`.
Sprawdza prawdziwy proces OCR i podmianę wyłącznie własnego, wygenerowanego dokumentu.

## Licencja

[AGPL-3.0-or-later](LICENSE). Zależności i ich licencje: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Kod źródłowy, skrypty budowania oraz wersje bibliotek są publiczne. Qt jest dołączony
jako wymienne biblioteki dynamiczne.
