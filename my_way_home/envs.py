import gym
import cv2
from vizdoom import *
import numpy as np

from abc import abstractmethod
from collections import deque
from copy import copy

#import gym_super_mario_bros
#from nes_py.wrappers import BinarySpaceToDiscreteSpaceEnv
#from gym_super_mario_bros.actions import SIMPLE_MOVEMENT, COMPLEX_MOVEMENT

from torch.multiprocessing import Pipe, Process

from model import *
from config import *
from PIL import Image

train_method = default_config['TrainMethod']
max_step_per_episode = int(default_config['MaxStepPerEpisode'])


class Environment(Process):
    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def pre_proc(self, x):
        pass

    @abstractmethod
    def get_init_state(self, x):
        pass


def unwrap(env):
    if hasattr(env, "unwrapped"):
        return env.unwrapped
    elif hasattr(env, "env"):
        return unwrap(env.env)
    elif hasattr(env, "leg_env"):
        return unwrap(env.leg_env)
    else:
        return env


class MaxAndSkipEnv(gym.Wrapper):
    def __init__(self, env, is_render, skip=4):
        """Return only every `skip`-th frame"""
        gym.Wrapper.__init__(self, env)
        # most recent raw observations (for max pooling across time steps)
        self._obs_buffer = np.zeros(
            (2, ) + env.observation_space.shape, dtype=np.uint8)
        self._skip = skip
        self.is_render = is_render

    def step(self, action):
        """Repeat action, sum reward, and max over last observations."""
        total_reward = 0.0
        done = None
        for i in range(self._skip):
            obs, reward, done, info = self.env.step(action)
            if self.is_render:
                self.env.render()
            if i == self._skip - 2:
                self._obs_buffer[0] = obs
            if i == self._skip - 1:
                self._obs_buffer[1] = obs
            total_reward += reward
            if done:
                break
        # Note that the observation on the done=True frame
        # doesn't matter
        max_frame = self._obs_buffer.max(axis=0)

        return max_frame, total_reward, done, info

    def reset(self, **kwargs):
        return self.env.reset(**kwargs)


class DoomEnvironment(Process):
    def __init__(self,
                 env_id,
                 is_render,
                 env_idx,
                 child_conn,
                 history_size=4,
                 life_done=True,
                 h=42,
                 w=42,
                 sticky_action=True,
                 p=0.25):
        super(DoomEnvironment, self).__init__()
        self.daemon = True
        self.is_render = is_render
        self.env_id = env_id
        self.env = self.init_game()
        self.env_idx = env_idx
        self.steps = 0
        self.episode = 0
        self.rall = 0
        self.recent_rlist = deque(maxlen=100)
        self.child_conn = child_conn

        self.life_done = life_done
        self.sticky_action = sticky_action
        self.last_action = 0
        self.p = p
        self.history_size = history_size
        self.history = np.zeros([history_size, h, w])
        self.img_shape = (h, w)
        self.h = h
        self.w = w
        
        self.a_size = 3
        if self.env_id == "battle":
            self.a_size = 4
            #print('scenarios is battle, action size is ', self.a_size)
        else:
            #print('scenarios is my way home action size is ', self.a_size)
            pass
            
        self.actions = self.button_combinations()
        self.reset()
    
    def init_game(self):
        game = DoomGame()
        if self.env_id == "my_way_home":
            game.load_config('../scenarios/my_way_home.cfg')
            game.clear_available_buttons()
            game.add_available_button(Button.MOVE_FORWARD)
            game.add_available_button(Button.TURN_LEFT)
            game.add_available_button(Button.TURN_RIGHT)

        elif self.env_id == "battle":
            game.load_config('../scenarios/D3_battle.cfg')
            game.clear_available_buttons()
            game.add_available_button(Button.MOVE_FORWARD)
            game.add_available_button(Button.TURN_LEFT)
            game.add_available_button(Button.TURN_RIGHT)
            game.add_available_button(Button.ATTACK)
            game.add_available_game_variable(GameVariable.AMMO2)
            game.add_available_game_variable(GameVariable.HEALTH)
            game.add_available_game_variable(GameVariable.USER2)
            
        game.set_doom_map('map01')
        game.set_screen_resolution(ScreenResolution.RES_640X480)
        game.set_screen_format(ScreenFormat.RGB24)
        game.set_render_hud(False)
        game.set_render_crosshair(False)
        game.set_render_weapon(True)
        game.set_render_decals(False)
        game.set_render_particles(True)
        # Enables labeling of the in game objects.
        game.set_labels_buffer_enabled(True)
        game.set_episode_timeout(2100)
        game.set_episode_start_time(5)
        game.set_window_visible(self.is_render)
        game.set_sound_enabled(False)
        game.set_living_reward(0)
        game.set_mode(Mode.PLAYER)
        game.init()
        return game
    
    def init_variables(self):
        self.health = 100
        self.kill = 0
        self.ammo = 50
    
    def get_variables(self):
        self.health = self.env.get_game_variable(GameVariable.HEALTH)
        self.kill = self.env.get_game_variable(GameVariable.KILLCOUNT)
        self.ammo = self.env.get_game_variable(GameVariable.AMMO2)

    def button_combinations(self):
        actions = np.identity(self.a_size, dtype=int).tolist()
        return actions

    def run(self):
        super(DoomEnvironment, self).run()
        #self.init_variables()
        while True:
            #print(self.env.get_game_variable(GameVariable.HEALTH))
            action = self.child_conn.recv()
            #TODO work on render
            # sticky action
            if self.sticky_action:
                if np.random.rand() <= self.p:
                    action = self.last_action
                self.last_action = action
                
            if self.is_render:
                reward = self.env.make_action(self.actions[action], 4)
            else:
                reward = self.env.make_action(self.actions[action], 4)

            self.get_variables()
            done = self.env.is_episode_finished()

            if not done:
                s = self.env.get_state().screen_buffer
            log_reward = reward
            force_done = done
            self.history[:3, :, :] = self.history[1:, :, :]
            self.history[3, :, :] = self.pre_proc(s)

            self.rall += reward
            self.steps += 1

            if done:
                self.recent_rlist.append(self.rall)
                if self.env_id == 'battle':
                    print(
                        "[Episode {}({})] Step: {}  Reward: {}  Recent Reward: {} Kill: {} Health: {} Ammunition: {}".format(
                            self.episode,
                            self.env_idx,
                            self.steps,
                            self.rall,
                            np.mean(self.recent_rlist),
                            self.kill,
                            self.health,
                            self.ammo))
                else:
                    print(
                        "[Episode {}({})] Step: {}  Reward: {}  Recent Reward: {}".format(
                            self.episode,
                            self.env_idx,
                            self.steps,
                            self.rall,
                            np.mean(self.recent_rlist)))

                self.history = self.reset()

            
            self.child_conn.send([self.history[:, :, :], reward, force_done, done, log_reward])

    def reset(self):
        self.env.new_episode()
        self.last_action = 0
        self.steps = 0
        self.episode += 1
        self.rall = 0
        self.env.new_episode()
        s = self.env.get_state().screen_buffer
        self.get_init_state(self.pre_proc(s))
        return self.history[:, :, :]
        

    def pre_proc(self, X):
        x = cv2.resize(X, self.img_shape)
        x = np.array(Image.fromarray(x).convert('L')).astype('float32')
        #x = cv2.resize(X, (self.h, self.w), interpolation=cv2.INTER_LINEAR)
        #x = np.dot(x[..., :3], [0.299, 0.587, 0.114])

        return x
    
    def get_init_state(self, s):
        for i in range(self.history_size):
            self.history[i, :, :] = self.pre_proc(s)


class MontezumaInfoWrapper(gym.Wrapper):
    def __init__(self, env, room_address):
        super(MontezumaInfoWrapper, self).__init__(env)
        self.room_address = room_address
        self.visited_rooms = set()

    def get_current_room(self):
        ram = unwrap(self.env).ale.getRAM()
        assert len(ram) == 128
        return int(ram[self.room_address])

    def step(self, action):
        obs, rew, done, info = self.env.step(action)
        self.visited_rooms.add(self.get_current_room())

        if 'episode' not in info:
            info['episode'] = {}
        info['episode'].update(visited_rooms=copy(self.visited_rooms))

        if done:
            self.visited_rooms.clear()
        return obs, rew, done, info

    def reset(self):
        return self.env.reset()


class AtariEnvironment(Environment):
    def __init__(self,
                 env_id,
                 is_render,
                 env_idx,
                 child_conn,
                 history_size=4,
                 h=42,
                 w=42,
                 life_done=True,
                 sticky_action=True,
                 p=0.25):
        super(AtariEnvironment, self).__init__()
        self.daemon = True
        self.env = MaxAndSkipEnv(gym.make(env_id), is_render)
        if 'Montezuma' in env_id:
            self.env = MontezumaInfoWrapper(
                self.env, room_address=3 if 'Montezuma' in env_id else 1)
        self.env_id = env_id
        self.is_render = is_render
        self.env_idx = env_idx
        self.steps = 0
        self.episode = 0
        self.rall = 0
        self.recent_rlist = deque(maxlen=100)
        self.child_conn = child_conn

        self.sticky_action = sticky_action
        self.last_action = 0
        self.p = p

        self.history_size = history_size
        self.history = np.zeros([history_size, h, w])
        self.h = h
        self.w = w

        self.reset()

    def run(self):
        super(AtariEnvironment, self).run()
        while True:
            action = self.child_conn.recv()

            if 'Breakout' in self.env_id:
                action += 1

            # sticky action
            if self.sticky_action:
                if np.random.rand() <= self.p:
                    action = self.last_action
                self.last_action = action

            s, reward, done, info = self.env.step(action)

            if max_step_per_episode < self.steps:
                done = True

            log_reward = reward
            force_done = done

            self.history[:3, :, :] = self.history[1:, :, :]
            self.history[3, :, :] = self.pre_proc(s)

            self.rall += reward
            self.steps += 1

            if done:
                self.recent_rlist.append(self.rall)
                print(
                    "[Episode {}({})] Step: {}  Reward: {}  Recent Reward: {}  Visited Room: [{}]"
                    .format(self.episode, self.env_idx, self.steps, self.rall,
                            np.mean(self.recent_rlist),
                            info.get('episode', {}).get('visited_rooms', {})))

                self.history = self.reset()

            self.child_conn.send(
                [self.history[:, :, :], reward, force_done, done, log_reward])

    def reset(self):
        self.last_action = 0
        self.steps = 0
        self.episode += 1
        self.rall = 0
        s = self.env.reset()
        self.get_init_state(self.pre_proc(s))
        return self.history[:, :, :]

    def pre_proc(self, X):
        x = np.array(Image.fromarray(X).convert('L')).astype('float32')
        x = cv2.resize(x, (self.h, self.w))
        return x

    def get_init_state(self, s):
        for i in range(self.history_size):
            self.history[i, :, :] = self.pre_proc(s)


'''
class MarioEnvironment(Process):
    def __init__(
            self,
            env_id,
            is_render,
            env_idx,
            child_conn,
            history_size=4,
            life_done=True,
            h=42,
            w=42, movement=COMPLEX_MOVEMENT, sticky_action=True,
            p=0.25):
        super(MarioEnvironment, self).__init__()
        self.daemon = True
        self.env = BinarySpaceToDiscreteSpaceEnv(
            gym_super_mario_bros.make(env_id), COMPLEX_MOVEMENT)

        self.is_render = is_render
        self.env_idx = env_idx
        self.steps = 0
        self.episode = 0
        self.rall = 0
        self.recent_rlist = deque(maxlen=100)
        self.child_conn = child_conn

        self.life_done = life_done
        self.sticky_action = sticky_action
        self.last_action = 0
        self.p = p

        self.history_size = history_size
        self.history = np.zeros([history_size, h, w])
        self.h = h
        self.w = w

        self.reset()

    def run(self):
        super(MarioEnvironment, self).run()
        while True:
            action = self.child_conn.recv()
            if self.is_render:
                self.env.render()

            # sticky action
            if self.sticky_action:
                if np.random.rand() <= self.p:
                    action = self.last_action
                self.last_action = action

            obs, reward, done, info = self.env.step(action)

            # when Mario loses life, changes the state to the terminal
            # state.
            if self.life_done:
                if self.lives > info['life'] and info['life'] > 0:
                    force_done = True
                    self.lives = info['life']
                else:
                    force_done = done
                    self.lives = info['life']
            else:
                force_done = done

            # reward range -15 ~ 15
            log_reward = reward / 15
            self.rall += log_reward

            r = log_reward

            self.history[:3, :, :] = self.history[1:, :, :]
            self.history[3, :, :] = self.pre_proc(obs)

            self.steps += 1

            if done:
                self.recent_rlist.append(self.rall)
                print(
                    "[Episode {}({})] Step: {}  Reward: {}  Recent Reward: {}  Stage: {} current x:{}   max x:{}".format(
                        self.episode,
                        self.env_idx,
                        self.steps,
                        self.rall,
                        np.mean(
                            self.recent_rlist),
                        info['stage'],
                        info['x_pos'],
                        self.max_pos))

                self.history = self.reset()

            self.child_conn.send([self.history[:, :, :], r, force_done, done, log_reward])

    def reset(self):
        self.last_action = 0
        self.steps = 0
        self.episode += 1
        self.rall = 0
        self.lives = 3
        self.stage = 1
        self.max_pos = 0
        self.get_init_state(self.env.reset())
        return self.history[:, :, :]

    def pre_proc(self, X):
        # grayscaling
        x = cv2.cvtColor(X, cv2.COLOR_RGB2GRAY)
        # resize
        x = cv2.resize(x, (self.h, self.w))

        return x

    def get_init_state(self, s):
        for i in range(self.history_size):
            self.history[i, :, :] = self.pre_proc(s)
'''
