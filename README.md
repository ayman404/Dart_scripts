# DART Scripts Documentation

Ce dossier contient des scripts Python permettant de configurer automatiquement les fichiers d’entrée nécessaires à la simulation avec le modèle DART. Les principaux scripts sont :

---

### `update_coeff_diff.py`

**Fonction** : Met à jour les propriétés optiques et thermiques.  
**Workflow** :

- Lit le nombre d'arbres (N) depuis `position.txt`.
- Crée le fichier `coeff_diff.xml` dans `simulation_path/input/`.
- Gère les propriétés optiques et thermiques :
  - Si `tree_temperature=true` : crée N températures de feuilles (`Temp_leaf_0` à `Temp_leaf_N-1`) et N températures de troncs (`Temp_trunk_0` à `Temp_trunk_N-1`).
  - Si `tree_temperature=false` : crée une plage de température unique (`Temperature_290_310`).
  - Ajoute toujours `Temp_soil`.
  - Si `chlorophyl=true` ou `water_thickness=true` : crée N propriétés optiques de feuilles (`leaf_0` à `leaf_N-1`).
  - Ajoute toujours la propriété optique du tronc.

---

### `update_objects.py`

**Fonction** : Met à jour la configuration des objets 3D des arbres.  
**Workflow** :

- Lit les positions des arbres depuis `position.txt`.
- Crée le fichier `object_3d.xml` dans `simulation_path/input/`.
- Pour chaque position d'arbre :
  - Sélectionne un fichier `.obj` :
    - Si `multi_tree=true` : sélection aléatoire.
    - Si `multi_tree=false` : utilise le premier fichier.
  - Crée l'objet avec :
    - Position et transformation depuis `position.txt`.
    - Groupes pour les feuilles et le tronc.
    - Liens vers les propriétés optiques :
      - Si `chlorophyl=true` ou `water_thickness=true` : `leaf_0` à `leaf_N-1`.
      - Sinon : `leaf_0` pour tous.
    - Toujours `"trunk"` pour le tronc.
    - Liens vers les propriétés thermiques :
      - Si `tree_temperature=true` : températures individuelles.
      - Sinon : `Temperature_290_310` pour tous.

---

### `update_maket.py`

**Fonction** : Met à jour le fichier `maket.xml` avec les propriétés du sol et des arbres.  
**Workflow** :

- Lit `config.json` et `coeff_diff.xml`.
- Modifie les liens vers les propriétés optiques et thermiques du sol.
- Crée une sauvegarde du fichier original (`maket.xml.backup`).
- Écrit un fichier XML propre avec indentation.

**Comportement** :

- Si `multi_sol=false` : utilise `"soil"`.
- Si `multi_sol=true` : récupère automatiquement les identifiants de sol disponibles dans `coeff_diff.xml` (`soil_0`, `soil_1`, etc.).

---

### `prepare_simulation.py`

**Fonction** : Prépare les fichiers nécessaires à la simulation, en s’assurant que toutes les configurations sont adéquates.  
**Workflow** :

- Lit la configuration dans `config.json`.
- Vérifie la présence et la validité des fichiers d'entrée (`position.txt`, `.obj`, etc.).
- Initialise et prépare les fichiers de simulation nécessaires à l'exécution du modèle DART.
- Gère les erreurs potentielles pour garantir une simulation sans interruption.

---

### `saveTIFF.py`

**Fonction** : Sauvegarde les résultats sous forme de fichiers TIFF.  
**Workflow** :

- Utilise la bibliothèque `rasterio` pour sauvegarder les données de simulation dans des fichiers TIFF.
- Vérifie que les dimensions des données sont correctes.
- Ajoute des métadonnées pour la traçabilité des résultats.
- Pour chaque séquence, génère :
  - Un fichier `sequence.tiff` (résultats de simulation).
  - Un fichier `props.json` (paramètres spécifiques à la séquence).

---

### `run_dart_sequence.py`

**Fonction** : Exécute une séquence complète de simulations DART.  
**Workflow** :

- Exécute les scripts précédents dans l'ordre recommandé.
- Lance les simulations en fonction des paramètres de `config.json`.
- Surveille le processus et génère des rapports d'exécution.

---

### `generate_contexte.py`

**Fonction** : Génère des cartes de propriétés (contextes) pour la simulation DART.  
**Workflow** :

- Charge la configuration depuis `config.json`.
- Lit les positions et échelles des arbres depuis `position.txt`.
- Génère des patches pour les propriétés comme :
  - Chlorophylle (Cab)
  - Épaisseur de l’eau (Cw)
  - Indice foliaire (LAI)
- Utilise la fonction `tree()` pour générer ces données.
- Crée une représentation tensorielle (`context.pt`) dans chaque dossier de `grp_path`.
- S'assure que les propriétés et les échelles sont bien configurées selon `config.json`.

---

Installation
-----------
Ces scripts nécessitent plusieurs packages Python pour fonctionner correctement. Pour installer toutes les dépendances ::

1. Assurez-vous d'avoir Python 3.7 ou une version supérieure installée.
2. Installez les packages requis en utilisant pip :
   ```
   pip install -r requirements.txt
   ```

3. Résolution de problèmes d'installation de rasterio et GDAL :
   - Les utilisateurs Windows peuvent avoir besoin d'installer les bibliothèques à partir de roues (wheels) : https://www.lfd.uci.edu/~gohlke/     pythonlibs/
   - Les utilisateurs Linux/Mac pourraient avoir besoin de dépendances système supplémentaires :
     ```
     # Pour Ubuntu/Debian
     sudo apt-get install libgdal-dev
     
     # Pour Mac (en utilisant Homebrew)
     brew install gdal
     ```

4. Vérification de l'installation:
Vérifiez l'installation en exécutant un test simple
   ```
   python -c "import rasterio; import numpy; print('Installation successful!')"
   ```

Configuration (config.json)
--------------------------
Les scripts utilisent un fichier de configuration partagé (config.json) avec la structure suivante :

{
    "paths": {
        "simulation_path": "Path to DART simulation directory",
        "position_txt_path": "Path to position.txt file",
        "tree_obj_path": "Path to directory containing tree .obj files"
    },
    "simulation_settings": {
        "multi_sol": false,
        "multi_tree": false,
        "run_sequencer": true
    },
    "parameters_to_vary": {
        "scale": false,
        "tree_temperature": false,
        "chlorophyl": false,
        "water_thickness": false,
        "soil_temperature": false
    }
}

Fichiers d’entrée
-----------
1. position.txt:
   - Contient les positions et les transformations des arbres
   - Format : index X Y Z Xscale Yscale Zscale Xrot Yrot Zrot
   - Chaque ligne représente la position et la transformation d'un arbre
   - Le nombre de lignes détermine le nombre d'arbres (N)

2. Fichiers .obj des arbres :
   - Situés dans tree_obj_path
   - Utilisés pour les modèles 3D des arbres
   - Si multi_tree=true : sélectionne aléatoirement différents modèles pour chaque arbre
   - Si multi_tree=false : utilise le premier fichier .obj pour tous les arbres

3. Lai.txt :
   - contient des valeurs de l'Indice de Surface Foliaire (LAI) pour différents modèles d'arbres


## Workflow

- **`update_coeff_diff.py`** : Lit `position.txt` pour déterminer le nombre d’arbres (N). Génère `coeff_diff.xml` avec les propriétés optiques et thermiques.
- **`update_objects.py`** : Lit `position.txt`, génère `object_3d.xml` et configure les groupes `leaves` et `trunk`.
- **`update_maket.py`** : Met à jour `maket.xml` avec les liens vers les propriétés, en créant une sauvegarde.
- **`prepare_simulation.py`** : Prépare les fichiers d’entrée et vérifie leur validité.
- **`saveTIFF.py`** : Sauvegarde les résultats dans `saveTIF/` avec `sequence.tiff` et `props.json`.
- **`run_dart_sequence.py`** : Exécute la simulation complète.
- **`generate_contexte.py`** : Génère les fichiers `context.pt` à partir des paramètres.

---

## Fichiers de sortie

- **`coeff_diff.xml`** : Propriétés optiques et thermiques.
- **`object_3d.xml`** : Positions et transformations des arbres.
- **`maket.xml`** : Liens vers les propriétés du sol et des objets.
- **Dossier `saveTIF/`** :
  - `sequence.tiff` : Résultat de simulation.
  - `props.json` : Paramètres de simulation.
- **`context.pt`** : Représentation tensorielle des propriétés (Cab, Cw, LAI, etc.).

---

## Utilisation

1. Configurez le fichier `config.json`.
2. Exécutez les scripts dans l’ordre recommandé :  
   - **`prepare_simulation.py`** : Prépare les fichiers d’entrée nécessaires selon la configuration définie par l'utilisateur.  
   - **`run_dart_sequence.py`** : Lance l’exécution complète de la simulation DART et de la séquence créée.  
   - **`generate_contexte.py`** : Génère les fichiers `context.pt` à partir des paramètres de simulation.

Assurez-vous que le fichier `config.json` est correctement configuré avant d’exécuter les scripts dans cet ordre .



