from Script import Port_Scanner
import cmd
from colorama import Fore, Style

class MyConsole(cmd.Cmd):
    intro = Fore.GREEN + "Welcome to Skim Framework! \nType help  to list commands." + Style.RESET_ALL
    prompt = Fore.BLUE + "myconsole> " + Style.RESET_ALL

    def do_use(self, arg):
        print(Fore.YELLOW + f"Loading module {arg}..." + Style.RESET_ALL)

    def do_set(self, arg):
        print(Fore.CYAN + f"Setting option: {arg}" + Style.RESET_ALL)

    def do_run(self, arg):
        print(Fore.GREEN + "Running..." + Style.RESET_ALL)

    def do_exit(self, arg):
        print(Fore.RED + "Exiting..." + Style.RESET_ALL)
        return True

    def emptyline(self):
        pass


