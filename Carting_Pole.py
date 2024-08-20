import gym

env = gym.make("FrozenLake-v1", render_mode="human")
env.reset
#Render the environment
env.render

#observation space - states
env.observation_space

# actions: left -0, down 1, right -2, up -3
env.action_space

#generate random action

randomAction = env.action_space.sample()
returnValue = env.step(randomAction)

env.render()

 