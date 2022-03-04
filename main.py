import tkinter as tk
from tkinter import messagebox
import requests
import protype
from dotenv import dotenv_values

env = dotenv_values(".env")
server = env["SERVER"]
def create_session(e):
    resp = requests.post(server + "session")
    uuid.set(resp.text)
def connect_protype():
    if uuid.get() == "":
        messagebox.showwarning(title="Distanstolkning saknas", message="Du måste skapa distanstolkningen först")
        return
    err = protype.connect(uuid.get())
    if err == 1:
        messagebox.showwarning(title="Sammanlänkning misslyckades", message="Har du startat ProType?")
        return

window = tk.Tk()
label = tk.Label(
    text="ProType - Distanstolkning",
    foreground="white",  # Set the text color to white
    background="black",  # Set the background color to black
    font=("Arial", 32)
)
label.grid(row=0, columnspan=6)

uuid = tk.StringVar()
password = tk.StringVar()
sessionLabel = tk.Label(text="Tolknings-ID")
sessionLabel.grid(row=2,column=0)
passwordLabel = tk.Label(text="Lösenord")
passwordLabel.grid(row=3,column=0)
create = tk.Button(text="Skapa distanstolkning")
create.bind("<Button-1>", create_session)
create.grid(row=1, column=1)
sessionEntry = tk.Entry(state="readonly", textvariable=uuid)
sessionEntry.grid(row=2, column=1)
passwordEntry = tk.Entry(textvariable=password)
passwordEntry.grid(row=3, column=1)

connect = tk.Button(text="Sammanlänka till ProType", command=connect_protype)
connect.grid(row=2, column=3, rowspan=3, columnspan=3)
copy = tk.Button(text="Kopiera uppgifter")
copy.grid(row=4, column=1)
window.mainloop()