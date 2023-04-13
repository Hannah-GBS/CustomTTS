import time
import tkinter as tk
from tkinter.messagebox import showerror
from tkinter import scrolledtext, font
import asyncio
import queue
import threading
import ttsController as TTS

dev_mode = True


class ttsGui(tk.Tk):
    def __init__(self, app: TTS):
        # TKinter setup
        super().__init__()

        # TTS Controller
        self.current_queue_list = []
        self.kill_flag = False
        self.app = app
        self.listener = ()

        def set_listener(listener: tuple):
            self.listener = listener

        self.queue = queue.Queue()

        # Frames  
        self.wm_title("Custom TTS")
        frm_queue = tk.Frame(self)
        frm_start = tk.Frame(self)

        # Pause button
        def toggle_pause():
            if pause_button.config('relief')[-1] == 'sunken':
                pause_button.config(relief='raised')
                self.app.pause_flag = False
            else:
                pause_button.config(relief='sunken')
                self.app.pause_flag = True

        pause_button = tk.Button(frm_queue, text="Pause", command=toggle_pause)
        pause_button.grid(column=1, row=0, pady=10, sticky=tk.E)

        # Clear queue button
        clear_button = tk.Button(frm_queue, text="Clear Queue", command=self.clear_queue)
        clear_button.grid(column=2, row=0, pady=10, sticky=tk.W)

        # Queue frame
        tk.Label(frm_queue, text="Queued TTS Messages").grid(column=0, row=1, columnspan=4, padx=10)
        font.nametofont('TkFixedFont').configure(family='Arial', size=12, weight='normal')
        self.queue_view = scrolledtext.ScrolledText(frm_queue, width=50, height=10, wrap=tk.WORD,
                                                    state='disabled', spacing3=2)
        self.queue_view.grid(column=0, row=2, columnspan=4)

        # Start frame
        frm_start.grid(padx=10, pady=10)
        tk.Label(frm_start, text="Enter Twitch username to authorize: ").grid(column=0, row=0, padx=10, pady=10)
        channel_entry = tk.Entry(frm_start)
        channel_entry.insert(0, self.app.get_channel())
        channel_entry.grid(column=1, row=0, padx=10, pady=10)

        def channel_entry_cmd():
            if channel_entry.get() != "":
                self.app.set_channel(channel_entry.get())
                threading.Thread(target=self.app.worker, daemon=True).start()
                set_listener(asyncio.run(self.app.run()))
                frm_queue.grid()
                frm_start.grid_forget()
            else:
                showerror(title='Error', message='You must enter a Twitch Username')

        tk.Button(
            frm_start,
            text="Connect to Twitch",
            command=channel_entry_cmd
        ).grid(column=0, row=2, columnspan=2, sticky=tk.E)

        self.dev_thread = None
        if dev_mode:
            self.dev_thread = threading.Thread(target=self.dev_input, daemon=True)
            self.dev_thread.start()

        self.refresh_thread = threading.Thread(target=self.refresh_queue, daemon=True)
        self.refresh_thread.start()

    def on_closing(self):
        if self.listener != ():
            asyncio.run(self.app.kill(self.listener))
        self.destroy()

    def refresh_queue(self):
        while True:
            with self.app.tts_queue.mutex:
                messages = [{'user': item['user_name'], 'message': item['chat_message']} for item in list(self.app.tts_queue.queue)]
                if messages == self.current_queue_list:
                    time.sleep(1)
                    continue
                self.queue_view['state'] = 'normal'
                if len(messages) == 0:
                    self.queue_view.delete('1.0', tk.END)

                if len(self.current_queue_list) != 0:
                    if self.current_queue_list[0] not in messages:
                        self.queue_view.delete('1.0', '1.end+1c')

                for message in messages:
                    if message not in self.current_queue_list:
                        name_width = font.nametofont('TkFixedFont').measure(message['user'] + ": ")
                        self.queue_view.tag_config(message['user'], lmargin2=name_width)
                        self.queue_view.insert(tk.END, message['user'] + ': ' + message['message'] + '\n', message['user'])

                self.current_queue_list = messages
                self.queue_view['state'] = 'disabled'

            time.sleep(1)

    def clear_queue(self):
        was_paused = self.app.pause_flag
        self.app.pause_flag = True
        while not self.app.tts_queue.empty():
            try:
                self.app.tts_queue.get(block=False)
            except queue.Empty:
                break
            self.app.tts_queue.task_done()
        # while True:
        #     try:
        #         self.app.tts_queue.get(timeout=0.1)
        #         self.app.tts_queue.task_done()
        #     except queue.Empty:
        #         break
        self.app.pause_flag = was_paused

    def dev_input(self):
        while True:
            dev_message = input("Enter message: ")
            self.app.tts_queue.put({'bits_used': 1, 'user_name': 'hannah_gbs', 'chat_message': dev_message})


if __name__ == "__main__":
    controller = TTS.ttsController()
    window = ttsGui(app=controller)
    window.protocol("WM_DELETE_WINDOW", window.on_closing)
    window.mainloop()
