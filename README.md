# Weselna Familiada

Lokalna aplikacja do weselnej gry w stylu teleturnieju. Działa na jednym komputerze: prowadzący obsługuje panel, a osobne okno tablicy można przenieść na telewizor lub projektor.

## Gotowa wersja dla Windows

Pobierz i rozpakuj [WeselnaFamiliada.zip](dist/WeselnaFamiliada.zip), a następnie uruchom `WeselnaFamiliada.exe` z rozpakowanego folderu. Python nie jest potrzebny.

Nie uruchamiaj EXE bezpośrednio z podglądu ZIP — najpierw rozpakuj cały folder, ponieważ zawiera on też dźwięki aplikacji.

## Uruchomienie z kodu źródłowego

W katalogu projektu uruchom:

```powershell
.\.venv\Scripts\python.exe .\familiada.py
```

## Zwykła runda

1. Wpisz pytanie, wybierz liczbę odpowiedzi (4–6), a następnie ich treść i punktację.
2. Kliknij **Pokaż tablicę**. Przycisk **Pełny ekran tablicy (projektor)** otwiera bezramkową tablicę dokładnie na pierwszym ekranie innym niż główny (to pewniejsze niż systemowy fullscreen Tkintera). Na jednym ekranie używa zwykłego pełnego ekranu. Klawisz `Esc` zawsze wraca do zwykłego okna.
3. Używaj przycisków **Odkryj**. Punkty rundy naliczają się automatycznie.
4. W razie pomyłki użyj **Cofnij ostatnie odkrycie** — odpowiedź zostanie ukryta, a jej punkty odjęte od sumy rundy.
5. Trzy błędy obsłużysz przyciskiem **Błąd**; **Wyczyść błędy** usuwa je z tablicy.
6. Na końcu wybierz **Przyznaj rundę → D1/D2**.

## Drużyny i wyniki

W sekcji **Wyniki drużyn** można nadać własne nazwy obu drużynom. Zatwierdź nazwę Enterem albo kliknięciem poza polem — pojawi się od razu na tablicy.

Ręczna korekta punktów (`−1`, pole wyniku, `+1`) jest domyślnie zablokowana. Kliknij **Punkty zablokowane — kliknij, aby odblokować**, aby ją włączyć. Automatyczne przyznawanie punktów za rundę działa niezależnie od tej blokady.

## Finał

Kliknij **Przejdź do finału**, a następnie **Importuj 5 pytań finałowych…**. Wybierz dokładnie pięć zwykłych plików TXT z pytaniami rund zasadniczych — po jednym pliku na pytanie finałowe.

- Zawodnik 1 ma 15 sekund, zawodnik 2 — 20 sekund.
- Panel ma wspólne przyciski poprzedniego/następnego pytania. Oba segmenty zawodników pracują na tym samym aktualnie wyświetlanym pytaniu.
- Panel prowadzącego pokazuje pełną listę możliwych odpowiedzi z punktami oraz dwa niezależne segmenty: **Zawodnik 1** i **Zawodnik 2**.
- Wpisz numer odpowiedzi z listy. `0` albo puste pole oznacza **brak odpowiedzi** i zapisuje 0 pkt.
- Prowadzący podaje wyłącznie numer odpowiedzi z listy, a aplikacja automatycznie przypisuje tekst i punktację. Drugi zawodnik nie może wybrać tego samego numeru co pierwszy; pojawia się wtedy sygnał powtórzenia.
- Numer `0` oznacza brak odpowiedzi; po odsłonięciu aplikacja pokazuje 0 pkt.
- Każdy segment ma własne przyciski odsłonięcia odpowiedzi i punktów. Odsłonięcie punktów dolicza wynik i odtwarza dzwoneczki.
- Zmiana aktywnego zawodnika otwiera pytanie 1 z tego samego zestawu, bez utraty odpowiedzi pierwszego zawodnika.
- **Pokaż podsumowanie finału** wyświetla na tablicy pełne podsumowanie: nazwy i wyniki obu drużyn, zwycięzcę albo remis oraz sumę i rezultat finału względem progu 200 punktów.

Przycisk **Wróć do rundy zasadniczej** opuszcza widok finału i przywraca zwykłe sterowanie.

Każdy wybrany plik musi mieć zwykły format pytania — z 4–6 odpowiedziami oraz punktami. Plik [przykladowe_pytanie.txt](questions/przykladowe_pytanie.txt) jest przykładem takiego formatu.

## Pytania w TXT

Przycisk **Wczytaj pytanie** obsługuje pliki `.txt` i `.json`. Pytania tekstowe znajdują się w katalogu `questions`.

Format pliku TXT:

```text
PYTANIE: Co goście weselni robią najczęściej po północy?

ODPOWIEDZI:
1. TAŃCZĄ — 38 pkt
2. JEDZĄ — 27 pkt
3. ROZMAWIAJĄ — 16 pkt
4. ROBIĄ ZDJĘCIA — 11 pkt
```

Plik musi zawierać pytanie oraz od 4 do 6 odpowiedzi. Przykład: [przykladowe_pytanie.txt](questions/przykladowe_pytanie.txt).

## Dźwięki

Katalog `assets/sounds` zawiera efekty WAV. Aplikacja automatycznie używa ich dla intra, dobrej odpowiedzi, błędu, końca rundy i końca czasu w finale.

WAV-y są odtwarzane kolejno w osobnym wątku, aby krótkie sygnały nie były ucinane przez opóźnienie głośnika Bluetooth.

Na dole panelu znajduje się **soundbar**, który tworzy przycisk odtwarzania dla każdego pliku WAV w tym katalogu. Przycisk **Dźwięki WAV…** pozwala dodatkowo ręcznie podmienić przypisania efektów.

## Zapis gry

Przycisk **Zapisz pytanie** zapisuje bieżący stan gry do JSON: pytanie, odpowiedzi, wyniki, nazwy drużyn i tryb finałowy. Wczytanie JSON przywraca zapisany stan, z wyjątkiem ręcznej edycji punktów — ta zawsze startuje z blokadą.
