# Vizdoom implement

This is repositories is learning how to slove sparse reward.

I use Vizdoom scenarios ```my way home``` to test my module, I follow this [reps](https://github.com/jcwleo/random-network-distillation-pytorch) and this [paper](https://arxiv.org/pdf/1810.12894.pdf).

## Train
```
$ cd my_way_home
$ ./train.sh
```

## Enjoy
```
$ cd my_way_home
$ python eval.py
```

After training the result is save on ```/my_way_home/models```