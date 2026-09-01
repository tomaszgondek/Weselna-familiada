# Weselna Familiada

Prosta aplikacja desktopowa w Pythonie/Tkinterze: panel prowadzącego i druga, pełnoekranowa tablica na telewizor lub projektor.

## Start

W katalogu projektu uruchom:

```powershell
.\.venv\Scripts\python.exe .\familiada.py
```

Jeśli Python jest dodany do systemowej zmiennej `PATH`, wystarczy też `python familiada.py`.

Nie wymaga instalowania pakietów. Tablica ma stylistykę matrycy LED inspirowaną klasycznymi teleturniejami, ale nie używa logotypów ani grafik programu. Na Windows krótkie efekty dźwiękowe działają od razu. Są to własne, proste sygnały — bez dołączania nagrań z programu.

## Obsługa

1. Wpisz pytanie oraz wybierz 4, 5 lub 6 odpowiedzi z punktami.
2. Kliknij **Pokaż tablicę**, przenieś jej okno na drugi ekran i włącz **Pełny ekran tablicy**. `Esc` wyłącza pełny ekran, `F11` go przełącza.
3. Odkrywaj odpowiedzi przyciskami panelu. Punkty rundy naliczają się automatycznie.
4. Przycisk „Przyznaj rundę” przenosi wynik rundy do wybranej drużyny.
5. Pytanie można zapisać i wczytać jako plik JSON.
6. Przycisk **▶ Zagraj intro** odtwarza `assets/sounds/intro-familiada.wav`. Pozostałe pliki w `assets/sounds` są automatycznie używane dla odkrycia, błędu i wygranej rundy.
7. Przycisk **Dźwięki WAV…** pozwala ewentualnie podmienić przypisane pliki WAV.
