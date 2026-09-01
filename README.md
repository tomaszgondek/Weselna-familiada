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
2. Kliknij **Pokaż tablicę**, przesuń drugie okno na ekran TV/projektora i użyj **Pełny ekran tablicy**. Klawisz `F11` przełącza pełny ekran, a `Esc` go wyłącza.
3. Używaj przycisków **Odkryj**. Punkty rundy naliczają się automatycznie.
4. W razie pomyłki użyj **Cofnij ostatnie odkrycie** — odpowiedź zostanie ukryta, a jej punkty odjęte od sumy rundy.
5. Trzy błędy obsłużysz przyciskiem **Błąd**; **Wyczyść błędy** usuwa je z tablicy.
6. Na końcu wybierz **Przyznaj rundę → D1/D2**.

## Drużyny i wyniki

W sekcji **Wyniki drużyn** można nadać własne nazwy obu drużynom. Zatwierdź nazwę Enterem albo kliknięciem poza polem — pojawi się od razu na tablicy.

Ręczna korekta punktów (`−1`, pole wyniku, `+1`) jest domyślnie zablokowana. Kliknij **Punkty zablokowane — kliknij, aby odblokować**, aby ją włączyć. Automatyczne przyznawanie punktów za rundę działa niezależnie od tej blokady.

## Finał

Kliknij **Przejdź do finału**. Panel zmieni sterowanie na finałowe, a tablica pokaże wyniki zawodników, cel 200 punktów i licznik czasu.

- Zawodnik 1 ma 15 sekund, zawodnik 2 — 20 sekund.
- Każdy zawodnik odpowiada na maksymalnie 5 pytań.
- Wybierz zawodnika, wczytaj lub wpisz pytanie, odkrywaj odpowiedzi i użyj **Dodaj punkty pytania**.
- **Nowe pytanie finałowe** czyści bieżące pytanie i przechodzi do kolejnego.
- Zmiana aktywnego zawodnika nie kasuje obecnie wyświetlanego pytania.
- Wczytanie pytania `.txt` w finale nie wyłącza finału ani nie resetuje wyników.

Przycisk **Wróć do rundy zasadniczej** opuszcza widok finału i przywraca zwykłe sterowanie.

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

Na dole panelu znajduje się **soundbar**, który tworzy przycisk odtwarzania dla każdego pliku WAV w tym katalogu. Przycisk **Dźwięki WAV…** pozwala dodatkowo ręcznie podmienić przypisania efektów.

## Zapis gry

Przycisk **Zapisz pytanie** zapisuje bieżący stan gry do JSON: pytanie, odpowiedzi, wyniki, nazwy drużyn i tryb finałowy. Wczytanie JSON przywraca zapisany stan, z wyjątkiem ręcznej edycji punktów — ta zawsze startuje z blokadą.
