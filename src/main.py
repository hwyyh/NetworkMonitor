
import tkinter as tk

from src.gui import NetworkMonitorGUI


def main():
    root = tk.Tk()
    NetworkMonitorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
