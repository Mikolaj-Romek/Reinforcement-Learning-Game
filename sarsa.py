import os
import glob
import json
import random
import time

class SARSA:
    def __init__(self, character_type):
        self.character_type = character_type
        self.epsilon = 0
        self.epsilon_decay = 0.999997
        self.epsilon_min = 0.0
        self.alpha = 0.1
        self.alpha_decay = 0.9999
        self.alpha_min = 0.01
        self.gamma = 0.9

        if character_type == "knight":
            self.actions = ['move_left', 'move_right', 'attack', 'block', 'maintain_block', 'idle']
            self.q_table_folder = 'knight_q_tables'
        elif character_type == "enemy":
            self.actions = ['move_left', 'move_right', 'shoot', 'idle']
            self.q_table_folder = 'q_tables'
        elif character_type == "bird":
            self.actions = [
                'move_up', 'move_down', 'move_left', 'move_right',
                'move_up_left', 'move_up_right', 'move_down_left', 'move_down_right',
                'activate_shield', 'idle'
            ]
            self.q_table_folder = 'bird_q_tables'
        elif character_type == "rogue":
            self.actions = ['move_left', 'move_right', 'far_attack', 'close_attack', 'idle']
            self.q_table_folder = 'rogue_q_tables'
        else:
            raise ValueError(f"Unknown character type: {character_type}")

        self.q_table = self.load_q_table()
        self.episode_count = self.get_latest_episode_count()

    def get_latest_episode_count(self):
        q_table_files = glob.glob(f'{self.q_table_folder}/*.json')
        if not q_table_files:
            return 0
        latest_file = max(q_table_files, key=os.path.getctime)
        return int(latest_file.split('_')[-1].split('.')[0]) + 1

    def load_q_table(self):
        q_table_files = glob.glob(f'{self.q_table_folder}/*.json')
        if not q_table_files:
            return {}
        
        # Extract episode numbers
        episode_numbers = []
        for file in q_table_files:
            try:
                episode_num = int(file.split('_')[-1].split('.')[0])
                episode_numbers.append((episode_num, file))
            except ValueError:
                continue
        
        if not episode_numbers:
            return {}
        
        # Get the file with the highest episode number
        latest_file = max(episode_numbers, key=lambda x: x[0])[1]
        print(f"Loading Q-table from: {latest_file}")
        with open(latest_file, 'r') as f:
            return json.load(f)

    def save_q_table(self):
        if not os.path.exists(self.q_table_folder):
            os.makedirs(self.q_table_folder)
        filename = f'{self.q_table_folder}/q_table_episode_{self.episode_count}.json'
        with open(filename, 'w') as f:
            json.dump(self.q_table, f, indent=2)
        print(f"Q-table saved as {filename}")

    def get_action(self, state):
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        else:
            return max(self.q_table[state], key=self.q_table[state].get)

    def update_q_table(self, state, action, reward, next_state, next_action):
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        if next_state not in self.q_table:
            self.q_table[next_state] = {a: 0 for a in self.actions}

        current_q = self.q_table[state][action]
        next_q = self.q_table[next_state][next_action]
        new_q = current_q + self.alpha * (reward + self.gamma * next_q - current_q)
        self.q_table[state][action] = new_q

    def get_best_action(self, state):
        if state not in self.q_table:
            self.q_table[state] = {a: 0 for a in self.actions}
        return max(self.q_table[state], key=self.q_table[state].get)
    
    def end_episode(self):
        self.episode_count += 1
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.epsilon_min)
        # self.alpha = max(self.alpha * self.alpha_decay, self.alpha_min)
