import time
from design.loading_screen import loading_screen
from design.loading_screen import clear_screen
from design.console import MyConsole
from design.banner import show_random_banner
from Script.Port_Scanner import *
def main():
    loading_screen()
    clear_screen()
    time.sleep(1)
    show_random_banner()
    MyConsole().cmdloop()

if __name__ == "__main__":
    main()