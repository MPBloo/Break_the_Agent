# Guide pour l'équipe

## Ce qui est prêt

| Élément | État |
|---|---|
| Environnement (physique, monde seedé, 7 outils, score) | Fait et testé |
| Serveur MCP (stdio et HTTP) | Fait, vérifié identique à l'exécution directe |
| Solution de référence | 0,82 de moyenne sur 10 seeds (rayon de score 6 m), minimum 0,67 sur 60 seeds |
| Baselines « ne rien faire » et « arrêt précoce » | 0,00 et 0,03 |
| Tests (23 tests, dont les tentatives de triche) | Tous passent |
| Interface de résultats | `results/report.html` |
| Sonnet 5.5, ancienne consigne | 9 parties : 0,708; sous la référence dans 8 cas sur 9 |
| Sonnet 5.5, consigne Canadair | 9 parties : 0,730 contre 0,879; sous la référence dans les 9 cas |
| Retest Canadair avec Sonnet 4.5 | 9 parties terminées : moyenne 0,315 contre 0,879 pour la référence, inférieur sur les 9 |
| Retests Canadair avec Haiku 5.5 en high | 18 parties sur 18 interrompues par le filtre avant tout largage : résultat non comparable |
| Refus des filtres de sécurité | Haiku 5.5 concerné; les deux Sonnet ont joué sous la consigne Canadair |
| Emballage Harbor | Généré, jamais lancé sous Docker |
| Entraînement d'un petit modèle | Seulement l'export des données |

## Ce qu'il reste à faire, dans l'ordre

1. **Vérifier l'emballage Harbor** sur une machine avec Docker :

   ```bash
   python harbor/make_tasks.py --seeds 3
   ```

2. **Lire les transcripts dans le rapport** et regarder la section « Where the points were
   lost ». Elle dit si le modèle perd ses points sur le choix des expériences, sur l'ajustement
   ou sur la visée.

3. **Recalibrer si besoin**, dans `bomber/config.py` :
   - le modèle est trop proche de la référence : baisser `score_radius` (6 vers 5) ;
   - le modèle est à zéro partout : monter `score_radius` (6 vers 10).

   Relancer ensuite `python run_eval.py`, puis les runs du modèle : les anciens transcripts ne
   sont plus valables après un changement de configuration (le rejeu le signale).

4. **Bonus** : exporter des parties de la référence (`python export_dataset.py`), affiner un
   petit modèle, puis le mesurer avec `run_llm.py --base-url ...`.

## Voir les résultats

Ouvrir `results/report.html` dans un navigateur : c'est un fichier unique, sans serveur, reconstruit
à chaque `python run_eval.py`.

## Trame de la démo (10 minutes)

1. **Le problème (1 min).** Un Canadair largue de l'eau sur un feu de forêt, et le vent déplace
   la charge pendant sa chute. Le point de largage doit tenir compte du vent à plusieurs altitudes.
   L'agent a 10 largages d'essai, puis 5 largages réels sans retour.
2. **L'environnement (2 min).** Montrer le briefing en bas du rapport : toute la physique est
   écrite, seuls six nombres sont cachés. Montrer les sept outils.
3. **La référence (2 min).** Ouvrir une partie de la référence dans le rapport : les 6 essais
   en air clair à trois altitudes, les 4 essais dans la fumée, la courbe d'erreur qui descend
   à 2 m, les cinq impacts à environ 1 m.
4. **L'agent (3 min).** Ouvrir une partie du modèle. Montrer la vue 3D d'une cible ratée, le
   tableau « vérité contre hypothèse », la rose des vents, puis la barre « où les points sont
   perdus ».
5. **L'intégrité de la récompense (1 min).** Le tableau des scores : ne rien faire 0, arrêt
   précoce 0,03, largage sans modèle 0. Citer les 23 tests.
6. **Reproductibilité (1 min).** Lancer `python run_eval.py` en direct : environ 30 secondes
   sans transcripts de modèles; leur rejeu complet prend plus longtemps.

## Trois phrases à garder en tête

- « La référence n'a rien de plus que l'agent : mêmes outils, même budget, même briefing. Elle
  gagne par la méthode. »
- « Chaque point perdu est rattaché à une décision : quelles expériences, quand arrêter
  d'ajuster, comment viser. »
- « Si on donne à la référence les expériences de l'agent, on voit combien ces expériences
  valaient. »

## Limites à dire franchement

- La charge est un point matériel, pas une colonne d'eau qui se fragmente.
- Le terrain est plat et l'avion n'a pas de dynamique de vol.
- Les cinq « heuristiques » du tableau sont des scripts, pas des modèles.
