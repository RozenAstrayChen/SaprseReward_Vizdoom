import cv2
import numpy as np
import matplotlib.pyplot as plt
from vizdoom import *
from PIL import Image


game = DoomGame()
game.load_config("../scenarios/basic.cfg")
game.set_screen_resolution(ScreenResolution.RES_640X480)
game.set_screen_format(ScreenFormat.RGB24)
game.init()

game.new_episode()
X = game.get_state().screen_buffer
print(X.shape)
x = np.array(Image.fromarray(X).convert('L')).astype('float32')
x = cv2.resize(x, (84, 84))
print('x',x.shape)

x1 = cv2.resize(X, (84, 84))
x1 = np.array(Image.fromarray(x1).convert('L')).astype('float32')
print('x1',x1.shape)

print('x1 is sample as x2 ?',(x==x).all())
'''
plt.imshow(x, cmap='gray')
plt.show()
'''
'''
x2 = cv2.resize(X, (84, 84), interpolation=cv2.INTER_LINEAR)
x2 = np.dot(x2[..., :3], [0.299, 0.587, 0.114])
print('x2', x2.shape)
plt.imshow(x2, cmap='gray')
plt.show()
'''

