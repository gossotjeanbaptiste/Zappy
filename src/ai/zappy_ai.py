# zappy_ai.py
import os
import random
import subprocess
import sys
import time

from logger import Logger
from network import NetworkClient


class ZappyAI:
    def __init__(self, host, port, team_name):
        self.ai_id = os.environ.get("ZAPPY_AI_ID", "1")
        self.children_spawned = 0
        self.log = Logger(self.ai_id)
        self.network = NetworkClient(host, port, self.log)
        self.team_name = team_name
        self.slots_available = 0
        self.map_width = 0
        self.map_height = 0
        self.pending_commands = 0
        self.sent_commands_queue = []
        self.inventory = {"food": 10, "linemate": 0, "deraumere": 0, "sibur": 0, "mendiane": 0, "phiras": 0, "thystame": 0}
        self.CRITICAL_FOOD_THRESHOLD = 8
        self.FORK_FOOD_THRESHOLD = 20
        self.MAX_FORKS = 2
        self.forks_done = 0
        self.items_on_current_tile = []
        self.last_look_result = []
        self.chase_steps = []
        self.state = "EXPLORING"
        self.level = 1
        self.elevation_requirements = {
            1: {"nb_players": 1, "linemate": 1, "deraumere": 0, "sibur": 0, "mendiane": 0, "phiras": 0, "thystame": 0},
            2: {"nb_players": 2, "linemate": 1, "deraumere": 1, "sibur": 1, "mendiane": 0, "phiras": 0, "thystame": 0},
            3: {"nb_players": 2, "linemate": 2, "deraumere": 0, "sibur": 1, "mendiane": 0, "phiras": 2, "thystame": 0},
            4: {"nb_players": 4, "linemate": 1, "deraumere": 1, "sibur": 2, "mendiane": 0, "phiras": 1, "thystame": 0},
            5: {"nb_players": 4, "linemate": 1, "deraumere": 2, "sibur": 1, "mendiane": 3, "phiras": 0, "thystame": 0},
            6: {"nb_players": 6, "linemate": 1, "deraumere": 2, "sibur": 3, "mendiane": 0, "phiras": 1, "thystame": 0},
            7: {"nb_players": 6, "linemate": 2, "deraumere": 2, "sibur": 2, "mendiane": 2, "phiras": 2, "thystame": 1}
        }

    def authenticate(self, max_retries=5):
        """Handshake Zappy, avec retry si l'équipe est momentanément pleine."""
        for attempt in range(max_retries):
            self.network.connect()
            welcome = self.network.read_line()
            if welcome != "WELCOME":
                self.log(f"[-] Serveur inconnu: {welcome}")
                sys.exit(1)
            self.network.send_command(self.team_name)
            slots_line = self.network.read_line()
            if slots_line == "ko":
                self.network.close()
                if attempt == max_retries - 1:
                    self.log(f"[-] Connexion refusée par le serveur : Équipe '{self.team_name}' complète ou invalide.")
                    sys.exit(1)
                self.log(f"[*] Équipe pleine, nouvelle tentative dans 1s ({attempt + 1}/{max_retries})...")
                time.sleep(1)
                continue
            self.slots_available = int(slots_line)
            dimensions = self.network.read_line().split()
            if len(dimensions) == 2:
                self.map_width, self.map_height = int(dimensions[0]), int(dimensions[1])
            self.log(f"[*] Initialisation réussie ! Équipe: {self.team_name} | Carte: {self.map_width}x{self.map_height}")
            return

    def send_action(self, cmd):
        """Envoie une action et l'enregistre de manière séquentielle."""
        self.network.send_command(cmd)
        self.pending_commands += 1
        self.sent_commands_queue.append(cmd)
        self.log(f"[-> ACTION] {cmd} (State: {self.state} | Pendings: {self.pending_commands})")
        if cmd == "Incantation":
            self.log(f"[Incantation] Lancement du rituel d'élévation (niveau {self.level} -> {self.level + 1})...")
        if cmd in ["Forward", "Left", "Right"]:
            self._clear_vision()

    def parse_response(self, response):
        """Analyse et décode textuellement la réponse du serveur."""
        response = response.strip()
        if response == "ok": return True
        if response == "ko": return False
        if response.startswith("[") and response.endswith("]"):
            clean = response[1:-1].strip()
            return [item.strip() for item in clean.split(",")] if clean else []
        return response

    def update_memory(self, cmd_sent, decoded_data):
        """Aiguille la réponse du serveur vers le bon traitement."""
        cmd = str(cmd_sent)
        if cmd == "Inventory":
            self._sync_inventory(decoded_data)
        elif cmd == "Look" and isinstance(decoded_data, list):
            self._sync_vision(decoded_data)
        elif cmd.startswith("Take ") and decoded_data is True:
            self._on_take(cmd.split()[1])
        elif cmd.startswith("Set ") and decoded_data is True:
            self._on_set(cmd.split()[1])
        elif cmd == "Fork" and decoded_data is True:
            self._spawn_new_ai()
        elif cmd == "Incantation":
            self._on_incantation_result(decoded_data)

    def _sync_inventory(self, data):
        # Tolère le format sans crochets ni virgules de notre serveur
        if isinstance(data, str):
            words = data.split()
            if len(words) >= 2 and len(words) % 2 == 0:
                data = [f"{words[i]} {words[i + 1]}" for i in range(0, len(words), 2)]
        if not isinstance(data, list):
            return
        synced = False
        for entry in data:
            parts = entry.split()
            if len(parts) != 2:
                continue
            name, qty = (parts[0], parts[1]) if parts[1].isdigit() else (parts[1], parts[0])
            if qty.isdigit() and name in self.inventory:
                self.inventory[name] = int(qty)
                synced = True
        if synced:
            self.log(f"[Survie] Énergie synchronisée -> Food en stock: {self.inventory['food']}")

    def _sync_vision(self, tiles):
        if tiles and not any("food " in str(x) for x in tiles[:1] if "player" not in str(x)):
            self.last_look_result = tiles
            self.items_on_current_tile = tiles[0].split()

    def _on_take(self, item):
        if item in self.inventory:
            self.inventory[item] += 1
            self.log(f"[Inventaire] +1 {item} -> Total: {self.inventory[item]}")
        if item in self.items_on_current_tile:
            self.items_on_current_tile.remove(item)

    def _on_set(self, item):
        if item in self.inventory:
            self.inventory[item] -= 1
            self.items_on_current_tile.append(item)
            self.log(f"[Sol] Déposé {item} pour incantation. Reste en sac: {self.inventory[item]}")

    def _on_incantation_result(self, data):
        if data is False:
            self.log("[Incantation] Échec du rituel (conditions non réunies à la vérification).")
        elif data is True or "Current level" in str(data):
            self._level_up(str(data))

    def _level_up(self, text):
        try:
            self.level = int(text.split(":")[-1].strip())
        except ValueError:
            self.level += 1
        self.log(f"[ÉLÉVATION] Félicitations ! Votre drone est passé Niveau {self.level} !")

    def _spawn_new_ai(self):
        """Lance un processus IA sur le slot ouvert par le Fork.

        L'enfant reste dans le groupe de processus du parent : un Ctrl+C
        dans le terminal stoppe donc toute la lignée d'un coup, alors que
        la mort en jeu du parent laisse les enfants continuer la partie.
        """
        self.log("[Reproduction] Œuf pondu, slot ouvert. Lancement d'une nouvelle IA...")
        main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        self.children_spawned += 1
        child_id = f"{self.ai_id}.{self.children_spawned}"
        try:
            subprocess.Popen(
                [sys.executable, main_script,
                 "-p", str(self.network.port),
                 "-n", self.team_name,
                 "-h", self.network.host],
                env=dict(os.environ, ZAPPY_AI_ID=child_id),
            )
            self.log(f"[Reproduction] IA {child_id} lancée ({self.forks_done}/{self.MAX_FORKS} forks utilisés).")
        except OSError as e:
            self.log(f"[-] Impossible de lancer la nouvelle IA : {e}")

    # --- Décision ---

    def decide_next_action(self):
        """Priorités : manger, forker, récolter, s'élever, explorer."""
        self._update_state()
        if "food" in self.items_on_current_tile:
            self._clear_vision()
            return "Take food"
        if self._should_fork():
            self.forks_done += 1
            return "Fork"
        if self.state == "EXPLORING":
            action = self._take_needed_stone() or self._try_elevation()
            if action:
                return action
        action = self._chase_food()
        if action:
            return action
        if "Look" in self.sent_commands_queue:
            return "Inventory"
        return self._hunt_food() if self.state == "SURVIVAL" else self._explore()

    def _chase_food(self):
        """Poursuit la nourriture vue au Look : tourner PUIS avancer."""
        if not self.chase_steps and self.last_look_result:
            direction = self._find_food_direction()
            if direction == "Forward":
                self.chase_steps = ["Forward"]
            elif direction:
                self.chase_steps = [direction, "Forward"]
        if not self.chase_steps:
            return None
        self._clear_vision()
        return self.chase_steps.pop(0)

    def _update_state(self):
        if self.inventory["food"] >= self.CRITICAL_FOOD_THRESHOLD:
            self.state = "EXPLORING"
        elif self.state != "SURVIVAL":
            self.log(f"[ALERTE SURVIE] Énergie critique ({self.inventory['food']} food). Mode chasse actif.")
            self.state = "SURVIVAL"

    def _clear_vision(self):
        self.last_look_result = []
        self.items_on_current_tile = []

    def _should_fork(self):
        return (self.state == "EXPLORING"
                and self.inventory["food"] >= self.FORK_FOOD_THRESHOLD
                and self.forks_done < self.MAX_FORKS
                and "Fork" not in self.sent_commands_queue)

    def _stone_requirements(self):
        reqs = self.elevation_requirements.get(self.level, {})
        return {stone: qty for stone, qty in reqs.items() if stone != "nb_players"}

    def _take_needed_stone(self):
        for stone, qty in self._stone_requirements().items():
            if self.inventory.get(stone, 0) < qty and stone in self.items_on_current_tile:
                self.items_on_current_tile.remove(stone)
                return f"Take {stone}"
        return None

    def _try_elevation(self):
        stones = self._stone_requirements()
        for stone, qty in stones.items():
            if self.inventory.get(stone, 0) + self.items_on_current_tile.count(stone) < qty:
                return None
        players_required = self.elevation_requirements.get(self.level, {}).get("nb_players", 1)
        if self.items_on_current_tile.count("player") < players_required:
            return None
        for stone, qty in stones.items():
            if self.items_on_current_tile.count(stone) < qty and self.inventory.get(stone, 0) > 0:
                return f"Set {stone}"
        return "Incantation"

    def _find_food_direction(self):
        """Calcule la direction de la nourriture selon la pyramide de vision."""
        if not self.last_look_result or not isinstance(self.last_look_result, list):
            return None
        for index, tile in enumerate(self.last_look_result):
            if index == 0 or "food" not in str(tile).split():
                continue
            v = 1
            while (v + 1) * (v + 1) <= index:
                v += 1
            center_tile = (v * v) + v
            if index == center_tile:
                return "Forward"
            return "Left" if index < center_tile else "Right"
        return None

    def _hunt_food(self):
        if not self.last_look_result:
            if random.random() < 0.20 and "Inventory" not in self.sent_commands_queue:
                return "Inventory"
            return "Look"
        self._clear_vision()
        return "Forward"

    def _explore(self):
        if any(cmd in ["Look", "Inventory"] for cmd in self.sent_commands_queue):
            return "Forward"
        rand = random.random()
        if rand < 0.60:
            return "Forward"
        if rand < 0.80:
            return "Look"
        if rand < 0.92:
            return random.choice(["Left", "Right"])
        return "Inventory"

    # --- Boucle principale ---

    def run(self):
        """Boucle réseau : 1 réponse lue -> mémoire à jour -> 1 action envoyée."""
        self.send_action("Inventory")
        self.send_action("Look")
        while True:
            response = self.network.read_line()
            if response == "dead":
                self.log("[-] L'IA est morte d'épuisement. Fin du programme.")
                break
            if self._is_async_event(response):
                continue
            self._process_response(response)
            # Gel du rituel : rien n'est envoyé tant que l'Incantation est en vol
            if "Incantation" in self.sent_commands_queue:
                continue
            if self.pending_commands < 2:
                next_cmd = self.decide_next_action()
                if next_cmd:
                    self.send_action(next_cmd)

    def _is_async_event(self, response):
        if response.startswith("message") or response.startswith("eject"):
            self.log(f"[Événement Asynchrone] Intercepté: {response}")
            return True
        if response.startswith("Elevation underway"):
            self.log("[Incantation] Rituel en cours, le drone est gelé...")
            return True
        return False

    def _process_response(self, response):
        if response.startswith("Current level"):
            self._finish_incantation(response)
        elif self.sent_commands_queue:
            cmd_sent = self.sent_commands_queue.pop(0)
            self.pending_commands -= 1
            self.update_memory(cmd_sent, self.parse_response(response))

    def _finish_incantation(self, response):
        # Le résultat arrive de manière asynchrone : on le rattache à
        # l'Incantation en vol au lieu de dépiler la commande de tête
        if "Incantation" in self.sent_commands_queue:
            self.sent_commands_queue.remove("Incantation")
            self.pending_commands -= 1
        self._level_up(response)
