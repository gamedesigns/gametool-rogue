import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QInputDialog, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
import json
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.backends.backend_qt5agg as backend_qt5agg
from matplotlib.figure import Figure
from dataclasses import dataclass, asdict

# Data Classes for game entities
@dataclass
class Character:
    name: str
    atk: int
    def_: int
    str_: int
    agi: int
    int_: int
    luc: int
    cri: int
    dmg: int
    level: int = 1
    exp: int = 0
    rank: int = 1
    attribute_points: int = 0

@dataclass
class Equipment:
    name: str
    slot: str
    atk_bonus: int
    def_bonus: int
    str_bonus: int
    agi_bonus: int
    int_bonus: int
    luc_bonus: int
    cri_bonus: int
    price: int
    rarity: str

@dataclass
class LootBox:
    name: str
    items: list
    drop_rates: list

class BattleSystem:
    def __init__(self):
        self.turn_order = []

    def calculate_damage(self, attacker, defender):
        base_damage = attacker.atk - defender.def_
        crit_roll = random.randint(1, 100)
        is_crit = crit_roll <= attacker.cri
        damage = max(0, base_damage * (2 if is_crit else 1))
        return damage, is_crit

    def battle_round(self, entities):
        results = []
        # Sort by AGI for turn order
        self.turn_order = sorted(entities, key=lambda x: x.agi, reverse=True)

        for attacker in self.turn_order:
            if attacker.dmg <= 0:
                continue
            # Find random living target
            valid_targets = [e for e in entities if e != attacker and e.dmg > 0]
            if not valid_targets:
                break

            target = random.choice(valid_targets)
            damage, is_crit = self.calculate_damage(attacker, target)
            target.dmg -= damage
            attacker.dmg -= damage
            results.append({
                'attacker': attacker.name,
                'target': target.name,
                'damage': damage,
                'target_remaining_hp': target.dmg,
                'is_crit': is_crit
            })

            if attacker.dmg <= 0:
                break

        return results

class EquipmentManager:
    def __init__(self, game_data):
        self.game_data = game_data
        self.inventory = {}
        self.equipped = {}

    def add_item(self, item_name):
        if item_name not in self.game_data.equipment:
            return False
        item = self.game_data.equipment[item_name]
        if item.slot not in self.inventory:
            self.inventory[item.slot] = []
        self.inventory[item.slot].append(item)
        return True

    def equip_item(self, slot, index):
        if slot not in self.inventory or index < 0 or index >= len(self.inventory[slot]):
            return False
        item = self.inventory[slot][index]
        if slot in self.equipped:
            unequipped_item = self.equipped[slot]
            for stat, bonus in asdict(unequipped_item).items():
                if stat.endswith('_bonus'):
                    char_attr = self.map_bonus_to_attribute(stat)
                    setattr(self.player, char_attr, getattr(self.player, char_attr) - bonus)
        self.equipped[slot] = item
        for stat, bonus in asdict(item).items():
            if stat.endswith('_bonus'):
                char_attr = self.map_bonus_to_attribute(stat)
                setattr(self.player, char_attr, getattr(self.player, char_attr) + bonus)
        return True

    def unequip_item(self, slot):
        if slot not in self.equipped:
            return False
        item = self.equipped[slot]
        for stat, bonus in asdict(item).items():
            if stat.endswith('_bonus'):
                char_attr = self.map_bonus_to_attribute(stat)
                setattr(self.player, char_attr, getattr(self.player, char_attr) - bonus)
        del self.equipped[slot]
        return True

    def map_bonus_to_attribute(self, bonus_attr):
        mapping = {
            'atk_bonus': 'atk',
            'def_bonus': 'def_',
            'str_bonus': 'str_',
            'agi_bonus': 'agi',
            'int_bonus': 'int_',
            'luc_bonus': 'luc',
            'cri_bonus': 'cri'
        }
        return mapping.get(bonus_attr, bonus_attr)

class GameData:
    def __init__(self):
        self.enemies = {
            'Mitochondria': Character(
                name='Mitochondria', atk=15, def_=10, str_=12,
                agi=8, int_=5, luc=5, cri=10, dmg=50
            ),
            'Ribosome': Character(
                name='Ribosome', atk=12, def_=8, str_=10,
                agi=12, int_=8, luc=6, cri=15, dmg=40
            ),
            'Lysosome': Character(
                name='Lysosome', atk=18, def_=5, str_=15,
                agi=6, int_=4, luc=4, cri=20, dmg=45
            )
        }

        self.equipment = {
            'Protein Catalyst': Equipment(
                name='Protein Catalyst', slot='weapon',
                atk_bonus=5, def_bonus=0, str_bonus=3,
                agi_bonus=2, int_bonus=0, luc_bonus=0,
                cri_bonus=5, price=100, rarity='Common'
            ),
            'Membrane Shield': Equipment(
                name='Membrane Shield', slot='shield',
                atk_bonus=0, def_bonus=8, str_bonus=2,
                agi_bonus=-1, int_bonus=0, luc_bonus=0,
                cri_bonus=0, price=120, rarity='Rare'
            ),
            'Legendary Sword': Equipment(
                name='Legendary Sword', slot='weapon',
                atk_bonus=10, def_bonus=5, str_bonus=5,
                agi_bonus=3, int_bonus=3, luc_bonus=3,
                cri_bonus=10, price=500, rarity='Legendary'
            )
        }

        self.loot_boxes = {
            'Basic Cell Drop': LootBox(
                name='Basic Cell Drop',
                items=['Protein Catalyst', 'Membrane Shield'],
                drop_rates=[0.7, 0.3]
            ),
            'Rare Cell Drop': LootBox(
                name='Rare Cell Drop',
                items=['Legendary Sword'],
                drop_rates=[1.0]
            )
        }

class WaveSystem:
    def __init__(self, game_data):
        self.game_data = game_data
        self.wave = 0
        self.enemies = []

    def generate_enemies(self):
        self.wave += 1
        enemy_count = self.wave * 2
        enemies = [self.game_data.enemies['Mitochondria'] for _ in range(enemy_count)]
        return enemies

class RogueGameTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game_data = GameData()
        self.battle_system = BattleSystem()
        self.equipment_manager = EquipmentManager(self.game_data)
        self.player = Character(
            name='Player', atk=20, def_=15, str_=15,
            agi=10, int_=10, luc=8, cri=10, dmg=100
        )
        self.equipment_manager.player = self.player
        self.wave_system = WaveSystem(self.game_data)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('RogueGameTool')
        self.setGeometry(100, 100, 1200, 800)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create entity editor
        entity_layout = QHBoxLayout()

        # Player column
        player_column = QVBoxLayout()
        player_label = QLabel('Player:')
        player_column.addWidget(player_label)

        self.player_stats_table = QTableWidget(8, 2)
        self.player_stats_table.setHorizontalHeaderLabels(['Stat', 'Value'])
        stats = ['ATK', 'DEF', 'STR', 'AGI', 'INT', 'LUC', 'CRI', 'DMG']
        for i, stat in enumerate(stats):
            self.player_stats_table.setItem(i, 0, QTableWidgetItem(stat))
        player_column.addWidget(self.player_stats_table)

        rank_label = QLabel('Rank:')
        player_column.addWidget(rank_label)
        self.rank_value = QLabel('1')
        player_column.addWidget(self.rank_value)

        attribute_points_label = QLabel('Attribute Points:')
        player_column.addWidget(attribute_points_label)
        self.attribute_points_value = QLabel('0')
        player_column.addWidget(self.attribute_points_value)

        entity_layout.addLayout(player_column)

        # Player stats graph
        self.canvas = Figure(figsize=(3, 2))
        self.ax = self.canvas.add_subplot(111)
        self.ax.set_title('Player Stats')

        self.canvas_widget = backend_qt5agg.FigureCanvasQTAgg(self.canvas)
        player_column.addWidget(self.canvas_widget)

        # Enemy selection
        enemy_group = QVBoxLayout()
        enemy_label = QLabel('Select Enemy:')
        self.enemy_combo = QComboBox()
        self.enemy_combo.addItems(self.game_data.enemies.keys())
        self.enemy_combo.currentTextChanged.connect(self.update_enemy_stats)
        enemy_group.addWidget(enemy_label)
        enemy_group.addWidget(self.enemy_combo)

        # Stats table
        self.stats_table = QTableWidget(8, 2)
        self.stats_table.setHorizontalHeaderLabels(['Stat', 'Value'])
        stats = ['ATK', 'DEF', 'STR', 'AGI', 'INT', 'LUC', 'CRI', 'DMG']
        for i, stat in enumerate(stats):
            self.stats_table.setItem(i, 0, QTableWidgetItem(stat))
        enemy_group.addWidget(self.stats_table)

        entity_layout.addLayout(enemy_group)

        # Shop system
        shop_group = QVBoxLayout()
        shop_label = QLabel('Shop:')
        shop_group.addWidget(shop_label)

        self.shop_table = QTableWidget(0, 3)
        self.shop_table.setHorizontalHeaderLabels(['Item', 'Price', 'Rarity'])
        shop_group.addWidget(self.shop_table)

        buy_button = QPushButton('Buy')
        buy_button.clicked.connect(self.buy_item)
        shop_group.addWidget(buy_button)

        sell_button = QPushButton('Sell')
        sell_button.clicked.connect(self.sell_item)
        shop_group.addWidget(sell_button)

        entity_layout.addLayout(shop_group)

        # Equipment management
        equipment_group = QVBoxLayout()
        equipment_label = QLabel('Equipment:')
        equipment_group.addWidget(equipment_label)

        self.inventory_table = QTableWidget(0, 3)
        self.inventory_table.setHorizontalHeaderLabels(['Slot', 'Item', 'Equipped'])
        equipment_group.addWidget(self.inventory_table)

        equip_button = QPushButton('Equip')
        equip_button.clicked.connect(self.equip_item)
        equipment_group.addWidget(equip_button)

        unequip_button = QPushButton('Unequip')
        unequip_button.clicked.connect(self.unequip_item)
        equipment_group.addWidget(unequip_button)

        entity_layout.addLayout(equipment_group)

        # Battle simulation
        battle_group = QVBoxLayout()
        battle_label = QLabel('Battle Configuration:')
        battle_group.addWidget(battle_label)

        self.wave_spin = QSpinBox()
        self.wave_spin.setMinimum(1)
        self.wave_spin.setMaximum(10)
        self.wave_spin.setValue(1)
        battle_group.addWidget(self.wave_spin)

        self.enemy_type_combo = QComboBox()
        self.enemy_type_combo.addItems(['Mitochondria', 'Ribosome', 'Lysosome'])
        battle_group.addWidget(self.enemy_type_combo)

        random_button = QPushButton('Random Waves')
        random_button.clicked.connect(self.random_waves)
        battle_group.addWidget(random_button)

        simulate_button = QPushButton('Simulate Battle')
        simulate_button.clicked.connect(self.simulate_battle)
        battle_group.addWidget(simulate_button)

        entity_layout.addLayout(battle_group)

        # Battle statistics
        battle_stats_group = QVBoxLayout()
        battle_stats_label = QLabel('Battle Statistics:')
        battle_stats_group.addWidget(battle_stats_label)

        self.battle_stats_table = QTableWidget(4, 2)
        self.battle_stats_table.setHorizontalHeaderLabels(['Stat', 'Value'])
        battle_stats = ['Hits', 'Misses', 'Criticals', 'Total Damage']
        for i, stat in enumerate(battle_stats):
            self.battle_stats_table.setItem(i, 0, QTableWidgetItem(stat))
        battle_stats_group.addWidget(self.battle_stats_table)

        entity_layout.addLayout(battle_stats_group)

        layout.addLayout(entity_layout)

        self.update_enemy_stats()
        self.update_inventory_table()
        self.update_player_stats()
        self.update_player_stats_graph()  # Ensure this is called after defining canvas_widget
        self.update_shop_table()

        # Style the stats tables
        self.style_stats_table(self.player_stats_table)
        self.style_stats_table(self.stats_table)
        self.style_stats_table(self.battle_stats_table)
        self.style_stats_table(self.shop_table)

    def style_stats_table(self, table):
        palette = table.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        table.setPalette(palette)

    def update_player_stats(self):
        stats = [
            self.player.atk, self.player.def_, self.player.str_, self.player.agi,
            self.player.int_, self.player.luc, self.player.cri, self.player.dmg
        ]
        for i, value in enumerate(stats):
            self.player_stats_table.setItem(i, 1, QTableWidgetItem(str(value)))
        self.rank_value.setText(str(self.player.rank))
        self.attribute_points_value.setText(str(self.player.attribute_points))

    def update_enemy_stats(self):
        enemy_name = self.enemy_combo.currentText()
        enemy = self.game_data.enemies[enemy_name]
        stats = [
            enemy.atk, enemy.def_, enemy.str_, enemy.agi,
            enemy.int_, enemy.luc, enemy.cri, enemy.dmg
        ]
        for i, value in enumerate(stats):
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(value)))

    def update_inventory_table(self):
        self.inventory_table.setRowCount(0)
        for slot, items in self.equipment_manager.inventory.items():
            for i, item in enumerate(items):
                row = self.inventory_table.rowCount()
                self.inventory_table.insertRow(row)
                self.inventory_table.setItem(row, 0, QTableWidgetItem(slot))
                self.inventory_table.setItem(row, 1, QTableWidgetItem(item.name))
                self.inventory_table.setItem(row, 2, QTableWidgetItem('Yes' if slot in self.equipment_manager.equipped and self.equipment_manager.equipped[slot] == item else 'No'))

    def equip_item(self):
        selected_row = self.inventory_table.currentRow()
        if selected_row < 0:
            return
        slot = self.inventory_table.item(selected_row, 0).text()
        if self.equipment_manager.equip_item(slot, selected_row):
            self.update_inventory_table()
            self.update_player_stats()
            self.update_player_stats_graph()

    def unequip_item(self):
        selected_row = self.inventory_table.currentRow()
        if selected_row < 0:
            return
        slot = self.inventory_table.item(selected_row, 0).text()
        if self.equipment_manager.unequip_item(slot):
            self.update_inventory_table()
            self.update_player_stats()
            self.update_player_stats_graph()

    def simulate_battle(self):
        wave_count = self.wave_spin.value()
        enemies = self.generate_enemies(wave_count)
        battle_results = self.battle_system.battle_round([self.player] + enemies)
        log_text = '\n'.join([
            f"{result['attacker']} attacks {result['target']} for {result['damage']} damage"
            for result in battle_results
        ])
        self.battle_log.setText(log_text)

        hits = sum(1 for result in battle_results if result['damage'] > 0)
        misses = len(battle_results) - hits
        criticals = sum(1 for result in battle_results if result['is_crit'])
        total_damage = sum(result['damage'] for result in battle_results)

        self.battle_stats_table.setItem(0, 1, QTableWidgetItem(str(hits)))
        self.battle_stats_table.setItem(1, 1, QTableWidgetItem(str(misses)))
        self.battle_stats_table.setItem(2, 1, QTableWidgetItem(str(criticals)))
        self.battle_stats_table.setItem(3, 1, QTableWidgetItem(str(total_damage)))

        if self.player.dmg <= 0:
            QMessageBox.warning(self, 'Game Over', 'You have been defeated!')
            return

        self.player.exp += len(enemies)  # Simple experience gain
        if self.player.exp >= self.player.rank * 10:
            self.player.rank += 1
            self.player.attribute_points += 1
            self.player.exp = 0

        self.update_player_stats()
        self.update_player_stats_graph()

    def update_player_stats_graph(self):
        # Extract relevant player stats as integers
        stats = [
            self.player.atk, self.player.def_, self.player.str_, self.player.agi,
            self.player.int_, self.player.luc, self.player.cri, self.player.dmg
        ]

        # Clear the current axis and create a new bar chart
        self.ax.clear()
        self.ax.bar(range(len(stats)), stats)

        # Set tick locations explicitly to match the number of stats
        self.ax.set_xticks(range(len(stats)))

        # Set tick labels with proper names for each stat
        self.ax.set_xticklabels(['ATK', 'DEF', 'STR', 'AGI', 'INT', 'LUC', 'CRI', 'DMG'])

        # Draw the canvas to update the graph using FigureCanvasQTAgg
        self.canvas_widget.draw()

    def update_shop_table(self):
        self.shop_table.setRowCount(0)
        for item_name, item in self.game_data.equipment.items():
            row = self.shop_table.rowCount()
            self.shop_table.insertRow(row)
            self.shop_table.setItem(row, 0, QTableWidgetItem(item_name))
            self.shop_table.setItem(row, 1, QTableWidgetItem(str(item.price)))
            self.shop_table.setItem(row, 2, QTableWidgetItem(item.rarity))

    def buy_item(self):
        selected_row = self.shop_table.currentRow()
        if selected_row < 0:
            return
        item_name = self.shop_table.item(selected_row, 0).text()
        if self.equipment_manager.add_item(item_name):
            self.update_inventory_table()
            self.update_player_stats()
            self.update_player_stats_graph()

    def sell_item(self):
        selected_row = self.inventory_table.currentRow()
        if selected_row < 0:
            return
        slot = self.inventory_table.item(selected_row, 0).text()
        item_name = self.inventory_table.item(selected_row, 1).text()
        if self.equipment_manager.remove_item(slot, item_name):
            self.update_inventory_table()
            self.update_player_stats()
            self.update_player_stats_graph()

    def random_waves(self):
        wave_count = random.randint(1, 10)
        enemies = self.generate_enemies(wave_count)
        self.simulate_battle(enemies)

    def generate_enemies(self, wave_count):
        enemies = []
        for _ in range(wave_count):
            enemy_type = random.choice(list(self.game_data.enemies.keys()))
            enemy = self.game_data.enemies[enemy_type]
            enemies.append(enemy)
        return enemies

def main():
    app = QApplication(sys.argv)
    tool = RogueGameTool()
    tool.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
