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


game = DoomGame()
game.load_config(cfg.SCENARIO_PATH)
game.set_doom_map("map01")
game.set_screen_resolution(ScreenResolution.RES_640X480)
game.set_screen_format(ScreenFormat.RGB24)
game.set_render_hud(False)
game.set_render_crosshair(False)
game.set_render_weapon(True)
game.set_render_decals(False)
game.set_render_particles(True)
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
#game.add_available_game_variable(GameVariable.USER2)
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
        print('action {}'.format(a))
        game.make_action(action_dim[a], 4)

def button_combinations():
    actions = []
    m_forward = [[True], [False]]  # move forward
    m_right_left = [[True, False], [False, True], [False, False]]  # move right and move left
    t_right_left = [[True, False], [False, True], [False, False]]  # turn right and turn left
    attack = [[True], [False]]
    speed = [[True], [False]]

    for i in m_forward:
        for j in m_right_left:
            for k in t_right_left:
                for m in attack:
                    for n in speed:
                        actions.append(i+j+k+m+n)
    return actions

#for i in range(0, a_num):
#    act(i)
print(len(button_combinations()))

game.close()