# Processus de mise à jour — Portail LREGE

## Structure des versions
- Format : `MAJEUR.MINEUR.CORRECTIF`
- Exemple : `1.2.3`
  - `1` → changement majeur (nouvelle fonctionnalité importante)
  - `2` → amélioration ou ajout mineur
  - `3` → correction de bug

---

## Étapes à suivre pour chaque MAJ

### 1. Modifier le code
Dans le dossier concerné :
- `SelecGE/` → sélections CDF
- `SYNESC/` → gestion des compétitions
- `EscriTools/` → outils escrime

### 2. Mettre à jour la version dans `setup.iss`
Ouvrir `setup.iss` avec Notepad et modifier :
```
#define AppVersion "X.X.X"
```

### 3. Sauvegarder sur GitHub
Double-clic sur `SAUVEGARDER.bat`, saisir un message clair :
```
SelecGE v1.1.0 - correction quota sabre laser seniors
```

### 4. Recompiler l'installeur
- Ouvrir `setup.iss` dans **Inno Setup Compiler**
- **Ctrl+F9**
- Le fichier `PortailLREGE_Setup_vX.X.X.exe` est généré dans `dist/`

### 5. Déposer sur Google Drive
- Dossier : `Drive > Releases > PortailLREGE_Setup_vX.X.X.exe`
- Conserver les versions précédentes

### 6. Informer les clubs
Envoyer un mail avec :
- Le lien Drive vers le nouvel installeur
- La description des changements
- La version précédente reste disponible sur le Drive

---

## Historique des versions

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | Avril 2026 | Version initiale — SelecGE + SYNESC + EscriTools |

---

## En cas de problème

### Revenir à une version précédente
```
git log --oneline
```
Repérer l'identifiant du commit souhaité, puis :
```
git checkout <id_commit>
```

### Rollback utilisateur
Les clubs peuvent télécharger une version précédente sur le Drive dans `Releases/`.

---

## Contacts
- Administration LREGE : administration@crege.fr
- Arbitrage LREGE : atrcrege@gmail.com
- Responsable technique : thomas.ducourant@gmail.com
