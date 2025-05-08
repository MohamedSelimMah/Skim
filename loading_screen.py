import os
import sys
import time
import random
from colorama import Fore,Style,init

init(autoreset=True)
name="ZeroOne"

def clear_screen():
    os.system('cls'if os.name=='nt' else 'clear')

def type_text(text,speed=0.05):
    for char in text:
        sys.stdout.write(Fore.CYAN + char + Style.RESET_ALL)
        sys.stdout.flush()
        time.sleep(speed)
    print()

def moving(name,width=60):
    for pos in range(width//2-len(name)//2):
        clear_screen()
        print(''*pos+Fore.LIGHTCYAN_EX+name+Style.RESET_ALL)
        time.sleep(0.02)

def fade_out(name):
    center_pos = (60-len(name))//2
    name_list= list(name)
    for  _ in range(len(name)):
        remove_idx = random.randint(0,len(name_list)-1)
        name_list[remove_idx]= ' '
        faded = ''.join(name_list)
        print(' '* center_pos + Fore.LIGHTBLACK_EX + faded+Style.RESET_ALL)
        time.sleep(0.02)


def glitch_effect(name, glitch_times=10):
    center_pos = (60 - len(name)) // 2
    glitch_chars = ['@', '#', '%', '&', '$', '*', '+', '-', '?']
    for _ in range(glitch_times):
        glitched = ''.join(
            random.choice(glitch_chars) if random.random() < 0.3 else c
            for c in name
        )
        clear_screen()
        print(' ' * center_pos + Fore.LIGHTYELLOW_EX + glitched + Style.RESET_ALL)
        time.sleep(0.05)

def loading_screen():
    clear_screen()
    type_text("[*] Starting up...")
    time.sleep(0.5)
    moving(name)
    glitch_effect(name)
    fade_out(name)
    clear_screen()
    print(Fore.GREEN + "[*] Welcome to the system." + Style.RESET_ALL)
