import time
from banner import *
from loading_screen import *
from console import *
def main():
    loading_screen()
    clear_screen()
    time.sleep(1)
    show_random_banner()
    MyConsole().cmdloop()

if __name__ == "__main__":
    main()