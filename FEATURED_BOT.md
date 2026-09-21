# Bot éditorial « à la une »

Cette seconde instance reprend les contrôles du bot éditorial principal sans partager son état ni son quota. Elle recherche un sujet important, rédige un article vérifié, génère une illustration locale, publie au maximum un article par jour (heure de Paris) et place le dernier article produit en première position sur l'accueil.

## Isolation

- Candidats : `data/featured_candidates.json`
- Registre public : `data/featured_articles.json`
- Dossiers de preuve privés : `data/featured_audit/`
- Illustrations : `actu-boxe/assets/img/featured/`
- Verrou : `data/.featured-publish.lock`
- Workflow : `.github/workflows/featured-editorial-cloud.yml`

Le quota est indépendant du bot principal. En revanche, les titres, slugs et sujets sont comparés à tous les articles manuels et automatiques afin d'éviter les doublons. Les mêmes exigences de sources, fraîcheur, traçabilité, originalité et relecture que dans `EDITORIAL_BOT.md` s'appliquent.

## Configuration privée

Pour une exécution locale, créer `.env.featured` à la racine du dépôt :

```dotenv
GROQ_FEATURED_API_KEY=valeur-privee
GROQ_FEATURED_RESEARCH_MODEL=openai/gpt-oss-20b
GROQ_FEATURED_WRITING_MODEL=openai/gpt-oss-120b
```

Le fichier est ignoré par Git. Dans GitHub, enregistrer la clé dans le secret de dépôt `GROQ_FEATURED_API_KEY`. Les modèles peuvent être personnalisés avec les variables de dépôt `GROQ_FEATURED_RESEARCH_MODEL` et `GROQ_FEATURED_WRITING_MODEL`.

Le workflow passe vers 14 h, heure de Paris. Les deux expressions UTC couvrent les changements d'heure ; une vérification locale de l'heure empêche le second passage. Une exécution manuelle reste possible depuis GitHub Actions.

## Commandes

```powershell
python featured_bot.py collect
python featured_bot.py status
python featured_editor.py
python build_pages.py
python -m unittest discover -s tests
```

L'article public porte `featured: true`. `build_pages.py` choisit l'article à la une le plus récent comme premier visuel de l'accueil. En l'absence d'article produit par cette instance, la une historique reste inchangée. Les URL des sources restent uniquement dans le dossier d'audit, hors du site publié.
