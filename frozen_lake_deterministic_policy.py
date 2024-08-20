import gym
import numpy as np
import matplotlib.pyplot as plt

# Add this line for compatibility
np.bool8 = np.bool_

env = gym.make('FrozenLake-v1')
policy ={
    0:1,
    1:2,
    2:1,
    3:0,
    4:1,
    6:1,
    8:2,
    9:1,
    10:1,
    13:2,
    14:2
}

n_games = 1000
win_pct = []
scores = []

for i in range(n_games):
    done = False
    obs, info = env.reset()
    score = 0
    while not done:
        action = policy[obs]
        obs, reward, terminated, truncated, info = env.step(action)
        score += reward
        done = terminated
    scores.append(score)
    
    if i % 10 == 0:
        average = np.mean(scores[-10:])
        win_pct.append(average)
        
plt.plot(win_pct)
plt.show()