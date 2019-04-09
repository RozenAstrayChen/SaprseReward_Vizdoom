# coding: utf-8
# implement of agent
import time
import random
import pickle
import itertools as iter

import numpy as np
import tensorflow as tf

from vizdoom import *

import utils
import configs as cfg
import random


game = DoomGame()
game.load_config(cfg.SCENARIO_PATH)
game.set_doom_map("map02")
game.set_screen_resolution(ScreenResolution.RES_640X480)
game.set_screen_format(ScreenFormat.RGB24)
#game.set_render_hud(False)
#game.set_render_crosshair(False)
#game.set_render_weapon(True)
#game.set_render_decals(False)
##game.set_render_particles(True)
# Enables labeling of the in game objects.
game.set_labels_buffer_enabled(True)
game.add_available_button(Button.MOVE_FORWARD)
game.add_available_button(Button.MOVE_RIGHT)
game.add_available_button(Button.MOVE_LEFT)
game.add_available_button(Button.TURN_LEFT)
game.add_available_button(Button.TURN_RIGHT)
game.add_available_button(Button.ATTACK)
#game.add_available_button(Button.SPEED)
game.add_available_game_variable(GameVariable.AMMO1)
game.add_available_game_variable(GameVariable.HEALTH)
game.add_available_game_variable(GameVariable.USER2)
game.set_episode_timeout(2100)
game.set_episode_start_time(5)
game.set_window_visible(True)
game.set_sound_enabled(False)
game.set_living_reward(0)
game.set_mode(Mode.PLAYER)
game.init()

a_num = game.get_available_buttons_size()
action_dim = np.identity(a_num,dtype=int).tolist()
game_vars = game.get_state().game_variables[:-1]
print(game_vars)
print(a_num)


def act(a):
    for i in range(0, 20):
        time.sleep(0.1)
        #print('action {}'.format(a))
        r = game.make_action(action_dim[a], 4)
        print('reward = ', r)

def rand_act(action_num):
    while not game.is_episode_finished():
        time.sleep(0.1)
        a = random.randint(0, action_num-1)
        r = game.make_action(action_dim[a], 4)
        print('reward = ', r)

'''
for i in range(0, a_num):
    act(i)
'''
action_num = len(cfg.button_combinations())

print(action_num)
rand_act(action_num)

game.close()