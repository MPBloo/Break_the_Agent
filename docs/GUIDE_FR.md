# Guide pour l'équipe

## Ce qui est prêt

| Élément | État |
|---|---|
| Environnement (physique, monde seedé, 7 outils, score) | Fait et testé |
| Serveur MCP (stdio et HTTP) | Fait, vérifié identique à l'exécution directe |
| Solution de référence | 0,89 de moyenne sur 10 seeds, jamais sous 0,80 sur 60 seeds |
| Baselines « ne rien faire » et « arrêt précoce » | 0,00 et 0,06 |
| Tests d'exploits (21 tests) | Tous passent |
| Interface de résultats | `results/report.html` |
| Boucle pour un modèle frontier (Gemini, etc.) | Écrite, testée seulement contre un faux serveur |
| Emballage Harbor | Généré, jamais lancé sous Docker |
| Entraînement d'un petit modèle | Seulement l'export des données |

## Ce qu'il reste à faire, dans l'ordre

1. **Lancer un vrai modèle.** C'est le point qui manque pour le critère « gap ».

   ```bash
   export LLM_API_KEY=...
   ```

   ```bash
   python run_llm.py --provider gemini --model <id du modèle> --seeds 3 --runs 3
   ```

   ```bash
   python run_eval.py
   ```

   Commencez par `--seeds 1 --runs 1` pour vérifier que l'API répond et voir le coût. Comptez
   1,5 à 3 millions de tokens d'entrée par partie sans cache.

2. **Lire les transcripts dans le rapport** et regarder la section « Where the points were
   lost ». Elle dit si le modèle perd ses points sur le choix des expériences, sur l'ajustement
   ou sur la visée.

3. **Recalibrer si besoin**, dans `bomber/config.py` :
   - le modèle est trop proche de la référence : baisser `score_radius` (10 vers 6) et
     `n_calculations` (120 vers 100) ;
   - le modèle est à zéro partout : monter `score_radius` (10 vers 15).

   Relancer ensuite `python run_eval.py`, puis les runs du modèle : les anciens transcripts ne
   sont plus valables après un changement de configuration (le rejeu le signale).

4. **Vérifier l'emballage Harbor** sur une machine avec Docker :

   ```bash
   python harbor/make_tasks.py --seeds 3
   ```

5. **Bonus** : exporter des parties de la référence (`python export_dataset.py`), affiner un
   petit modèle, puis le mesurer avec `run_llm.py --base-url ...`.

## Trame de la démo (10 minutes)

1. **Le problème (1 min).** Un largage d'eau tombe là où l'air l'emmène. Les militaires
   calculent le point de largage à partir de sondes de vent ; c'est le même schéma. L'agent a
   10 largages d'essai, puis 5 largages réels sans retour.
2. **L'environnement (2 min).** Montrer le briefing en bas du rapport : toute la physique est
   écrite, seuls six nombres sont cachés. Montrer les sept outils.
3. **La référence (2 min).** Ouvrir une partie de la référence dans le rapport : les 6 essais
   en air clair à trois altitudes, les 4 essais dans la fumée, la courbe d'erreur qui descend
   à 2 m, les cinq impacts à environ 1 m.
4. **L'agent (3 min).** Ouvrir une partie du modèle. Montrer la vue 3D d'une cible ratée, le
   tableau « vérité contre hypothèse », la rose des vents, puis la barre « où les points sont
   perdus ».
5. **L'intégrité de la récompense (1 min).** Le tableau des scores : ne rien faire 0, arrêt
   précoce 0,06, largage sans modèle 0. Citer les 21 tests.
6. **Reproductibilité (1 min).** Lancer `python run_eval.py` en direct : 30 secondes.

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
