# Kindle dashboard

Immagine 600×800 per Kindle: meteo di Mondovì (Open-Meteo) e parola italiana del giorno.
GitHub Actions la rigenera ogni ora e la pubblica su GitHub Pages.
Orologio e data li disegna direttamente il Kindle (`kindle/dashboard/dash.sh`).

- `render.py` – genera l'immagine (`--preview` aggiunge un orologio d'esempio)
- `parole.json` – elenco delle parole del giorno
- `kindle/` – file da copiare nella root del Kindle

Font: Inter e Playfair Display (SIL Open Font License).
