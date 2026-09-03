# Weselna Familiada — instrukcja obsługi

Program służy do prowadzenia weselnej gry w stylu Familiady. Prowadzący obsługuje panel sterujący, a osobne okno **tablicy** wyświetla się uczestnikom na telewizorze lub projektorze.

Nie wymaga instalowania Pythona ani żadnych dodatkowych programów.

## Uruchomienie

1. Rozpakuj cały plik ZIP do wybranego folderu.
2. Nie przenoś ani nie usuwaj podfolderów `assets` i `questions`.
3. Uruchom `WeselnaFamiliada.exe`.

> Nie uruchamiaj programu bezpośrednio z podglądu ZIP-a. Dźwięki i pytania muszą pozostać obok EXE w rozpakowanym folderze.

Po uruchomieniu pojawią się dwa okna:

- **Familiada — panel prowadzącego** — to tutaj sterujesz grą.
- **Familiada — TABLICA** — to okno dla gości.

## Tablica na telewizorze lub projektorze

1. Podłącz drugi ekran w Windows i ustaw go jako **Rozszerz te ekrany**.
2. W panelu prowadzącego kliknij **Pełny ekran tablicy (projektor)**.
3. Program umieści tablicę na pierwszym ekranie innym niż ekran główny.
4. Klawisz `Esc`, gdy aktywne jest okno tablicy, wychodzi z pełnego ekranu.

Przycisk **Pokaż tablicę** przywraca ukryte okno tablicy bez przechodzenia na pełny ekran.

## Zwykła runda

1. W polu **PYTANIE** wpisz pytanie.
2. Wybierz liczbę odpowiedzi: od 4 do 6.
3. Wpisz odpowiedzi i ich punktację.
4. Kliknij **Pokaż tablicę** albo wyświetl ją na projektorze.
5. Podczas gry klikaj **Odkryj 1**, **Odkryj 2** itd. Punkty są automatycznie doliczane do sumy rundy.
6. Za złą odpowiedź kliknij **Błąd**. Na tablicy pojawi się znak błędu. **Wyczyść błędy** usuwa wszystkie trzy znaki.
7. Jeśli coś odkryjesz przez pomyłkę, użyj **Cofnij ostatnie odkrycie**. Program ukryje odpowiedź i odejmie jej punkty od sumy rundy.
8. Na końcu kliknij **Przyznaj rundę → D1** lub **Przyznaj rundę → D2**. Punkty rundy zostaną dopisane do wybranej drużyny.

## Drużyny i ręczna korekta punktów

W sekcji **Wyniki drużyn**:

- wpisz nazwy drużyn w polach po lewej i prawej stronie;
- zatwierdź nazwę Enterem albo kliknięciem poza polem;
- użyj `−1`, pola wyniku albo `+1`, jeżeli trzeba poprawić wynik ręcznie.

Ręczna edycja wyniku jest domyślnie zablokowana. Najpierw zaznacz **Odblokuj edycję punktów**. Nie wpływa to na automatyczne przyznawanie punktów za rundę.

## Wczytywanie pytań

Kliknij **Wczytaj pytanie** i wybierz plik TXT z folderu `questions`. Można też użyć pliku JSON zapisanego przez program.

Format pytania TXT:

```text
PYTANIE: Co goście weselni robią najczęściej po północy?

1. TAŃCZĄ — 38 pkt
2. JEDZĄ — 27 pkt
3. ROZMAWIAJĄ — 16 pkt
4. ROBIĄ ZDJĘCIA — 11 pkt
```

Każdy plik musi mieć od 4 do 6 odpowiedzi. Możesz tworzyć własne pliki TXT według tego wzoru i dodawać je do folderu `questions`.

## Dźwięki

- **Zagraj intro** uruchamia muzykę otwarcia.
- Przy odkryciu odpowiedzi, błędzie, przyznaniu rundy i finale program odtwarza przypisane efekty automatycznie.
- Dolny **soundbar** zawiera przyciski do ręcznego odtworzenia wszystkich plików WAV z folderu `assets\\sounds`.
- Przycisk **Dźwięki WAV…** umożliwia wskazanie innych plików dla najważniejszych efektów.

Przy głośniku Bluetooth dźwięki są odtwarzane kolejno, dzięki czemu krótkie sygnały nie powinny być ucinane.

## Finał

Finał używa dokładnie pięciu zwykłych pytań. W finale gra dwóch zawodników zwycięskiej drużyny.

### Przygotowanie

1. Kliknij **Przejdź do finału**.
2. Kliknij **Importuj 5 pytań finałowych…**.
3. Wskaż dokładnie pięć plików TXT z pytaniami rund zasadniczych.

Panel pokaże pełną listę możliwych odpowiedzi i punktów dla aktualnego pytania. Uczestnicy nie widzą tej listy — widzi ją tylko prowadzący.

### Zawodnik 1

1. Dla każdego z pięciu pytań wpisz w panelu numer wybranej odpowiedzi z listy.
2. Kliknij **Zapisz odpowiedź**.
3. Przycisk **Start 15 s** uruchamia odliczanie dla pierwszego zawodnika.
4. Po zebraniu odpowiedzi odsłaniaj je przyciskiem **Odsłoń odpowiedź**, a następnie **Odsłoń punkty**.

### Zawodnik 2

1. W prawym segmencie wpisuj numery odpowiedzi drugiego zawodnika dla tych samych pięciu pytań.
2. Przycisk **Start 20 s** uruchamia jego czas.
3. Jeśli wybierze ten sam numer odpowiedzi co zawodnik 1 przy tym samym pytaniu, program odtworzy sygnał i nie zapisze wyboru — należy podać inną odpowiedź.
4. Odsłaniaj odpowiedzi i punkty tak samo jak dla zawodnika 1.

W polu numeru odpowiedzi wpisanie `0` lub pozostawienie pustego pola oznacza **brak odpowiedzi**. Po odsłonięciu zostanie pokazane 0 pkt.

Punkty obu zawodników sumują się. Cel finału to **200 punktów**. Przycisk **Pokaż podsumowanie finału** wyświetla końcowy ekran z wynikiem finału oraz wynikiem drużyn.

## Powrót z finału

Kliknij **Wróć do rundy zasadniczej**. Program przywróci pytanie i stan zwykłej rundy, który był widoczny przed wejściem do finału, włącznie z odkrytymi odpowiedziami, punktami rundy i błędami.

## Zapis gry

**Zapisz pytanie** zapisuje bieżący stan do pliku JSON: pytanie, odpowiedzi, wyniki drużyn, nazwy oraz stan finału. Taki plik można później otworzyć przez **Wczytaj pytanie**.
