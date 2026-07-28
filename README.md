<div align="center">

# 🐜 Zappy

### La civilisation Trantorienne n'attend que vous.

Un serveur de jeu massivement concurrent, une intelligence artificielle autonome et une interface 3D immersive — le tout batî pour faire évoluer des colonies de Zappies jusqu'à la transcendance.

</div>

---

## 🎯 Le projet

**Zappy** est un jeu multijoueur en temps réel où plusieurs équipes s'affrontent sur une carte torique (les bords se rejoignent, comme une planète) à la recherche de ressources rares. L'objectif : faire progresser au moins **6 joueurs d'une même équipe jusqu'au niveau maximal** avant que les équipes adverses n'y parviennent.

Le projet repose sur trois briques indépendantes qui communiquent entre elles via un protocole réseau maison :

| Composant | Rôle | Stack |
|---|---|---|
| 🖥️ **`zappy_server`** | Le cœur du jeu : logique, ressources, joueurs, incantations, arbitrage des règles | C — mono-thread, `poll()` |
| 🎮 **`zappy_gui`** | Visualisation temps réel du monde, des joueurs et des ressources en 3D | C++ |
| 🤖 **`zappy_ai`** | Intelligence artificielle pilotant un joueur de façon autonome | Python |

---

## ✨ Points forts

- **Zéro attente active** — le serveur ne consomme aucune ressource CPU inutilement : une unique boucle `poll()` orchestre tous les clients connectés.
- **Un monde vivant** — les ressources (`food`, `linemate`, `deraumere`, `sibur`, `mendiane`, `phiras`, `thystame`) réapparaissent dynamiquement toutes les 20 unités de temps.
- **Un protocole ouvert** — n'importe quel client (IA ou GUI) peut se connecter en TCP et dialoguer avec le serveur dès lors qu'il respecte le protocole.
- **Une IA stratégique** — gestion autonome de la survie, de la collecte de ressources et des rituels d'élévation collective.
- **Une GUI 3D** — rendu en temps réel de la carte, des joueurs, des œufs et des événements de jeu.
- **Une architecture scalable** — plusieurs équipes, plusieurs joueurs par équipe, un nombre de connexions uniquement limité par la configuration du serveur.

---

## 🚀 Démarrage rapide

### Compilation

```bash
make          # compile les trois binaires : zappy_server, zappy_gui, zappy_ai
```

Cibles disponibles :

```bash
make zappy_server   # uniquement le serveur
make zappy_gui      # uniquement l'interface graphique
make zappy_ai       # uniquement l'IA
make clean          # nettoie les objets de compilation
make fclean         # nettoie tout, y compris les binaires
make re             # fclean + all
```

### Lancer une partie

**1. Démarrer le serveur**

```bash
./zappy_server -p <port> -x <width> -y <height> -n <team1> <team2> ... -c <clientsNb> -f <freq>
```

| Flag | Description |
|---|---|
| `-p` | Port d'écoute du serveur |
| `-x` `-y` | Largeur / hauteur de la carte |
| `-n` | Noms des équipes en compétition |
| `-c` | Nombre de connexions autorisées par équipe |
| `-f` | Fréquence de jeu (unités de temps par seconde) |

**2. Connecter la GUI**

```bash
./zappy_gui -p <port> -h <hostname>
```

**3. Connecter une IA**

```bash
./zappy_ai -p <port> -n <team_name> -h <hostname>
```

---

## 🌍 Le monde de Zappy

La carte est **torique** : un joueur qui sort par la droite réapparaît à gauche, et de même verticalement. Chaque équipe doit s'organiser pour :

1. **survivre** — se nourrir avant l'épuisement des réserves de vie ;
2. **collecter** — accumuler les pierres précieuses disséminées sur la carte ;
3. **s'élever** — réunir les bonnes ressources et le bon nombre de joueurs de même niveau pour déclencher une incantation.

Les joueurs disposent d'un jeu de commandes restreint (`Forward`, `Right`, `Left`, `Look`, `Inventory`, `Broadcast`, `Fork`, `Eject`, `Take`, `Set`, `Incantation`, `Connect_nbr`), chacune ayant un coût en temps défini par la fréquence du serveur.

---

## 👥 L'équipe

Ce projet a été développé par :

- **Jean-Baptiste Gossot**
- **Nathan Claudel**
- **Victor Jost**
- **Ethan Wiss**
- **Antoine Schoeser**

---

## 📄 Licence

Projet réalisé dans le cadre du cursus **Epitech** (G-YEP-400). Base de code originale, propre et maintenable, conçue pour durer au-delà de la contrainte académique.

</content>
