import os

from PIL import Image, ImageDraw
import tkinter as tk
import datetime
from pynput import mouse
from typing import Tuple, Dict
import numpy as np

Position = Tuple[int, int]
Size = Tuple[int, int]
Color = Tuple[int, int, int, int]
Canvas_Width = 800
Canvas_Height = 600

class Colors:
    Left = (0, 255, 0, 100)
    Right = (255, 0, 0, 100)
    Middle = (255, 255, 0, 100)

Color_dict = {Colors.Left:'green', Colors.Right:'red', Colors.Middle:'blue'}

class Button(tk.Button):
    def __init__(self, *args, **kwarges):
        super(Button, self).__init__(*args, **kwarges)
        self.pack(pady=10)
        self["state"] = "normal"

    # Swith the state of the start/stop button
    def switch(self):
        self["state"] = "disable" if self["state"] == "normal" else "normal"

class Checkbutton(tk.Checkbutton):
    def __init__(self, *args, **kwargs):
        super(Checkbutton, self).__init__(*args, **kwargs)
        self.pack(pady=2)


class ImageCache(object):
    def __init__(self, size: Size):
        """Image Cache"""
        self._size = size
        self._refresh()

    @property
    def cache(self):
        return self._cache

    def _refresh(self):
        self._cache = Image.new(
            "RGBA",
            self._size,
            (0, 0, 0, 255),
        )
    
    def save(self, dirname="out", create_dir=True, clean=True):
        """
        Save the image
        Parameters:
        - dirname: the child dir name relative to the python file's parent dir for output
        - create_dir: whether to try creating or not
        - clean: whether to clean the cache or not
        """
        dir_path = os.path.join(os.path.dirname(__file__), dirname)
        if create_dir:
            os.makedirs(dir_path, exist_ok=True)
        elif not os.path.exists(dir_path):
            raise FileNotFoundError

        now = datetime.datetime.now()
        file_path = os.path.join(
            dir_path,
            f"mouse_track-{now.year}-{now.month}-{now.day}-{now.hour}-{now.minute}-{now.second}.png",
        )
        self.cache.save(file_path)

        if clean:
            self._refresh()
        print(f"轨迹图像已保存: {file_path}")


    def line(self, start: Position, end: Position):
        """
        Draw a line
        Parameters:
        - start: tuple of the line's start
        - end: tuple of the line's end
        """
        self._draw_transp_line(xy=[start, end], fill=(255, 255, 255, 50), width=2)

    def ellipse(self, x, y, color: Color, radius=10):
        """
        Draw a point at `(x, y)`
        :param x:
        :param y:
        :param color: format in R, G, B ,A
        :param radius:
        :return: None
        """
        self._draw_transparent_ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            fill=color,
        )

    def _draw_transp_line(self, xy, **kwargs):
        """
        Draws a line inside the given bounding box onto given image.
        Supports transparent colors
        """
        transp = Image.new("RGBA", self._size, (0, 0, 0, 0))  # Temp drawing image.
        draw = ImageDraw.Draw(transp, "RGBA")
        draw.line(xy, **kwargs)
        # Alpha composite two images together and replace first with result.
        self._cache.paste(Image.alpha_composite(self._cache, transp))
        

    def _draw_transparent_ellipse(self, xy, **kwargs):
        """
        Draws an ellipse inside the given bounding box onto given image.
        Supports transparent colors
        https://stackoverflow.com/a/54426778
        """
        transp = Image.new("RGBA", self._size, (0, 0, 0, 0))  # Temp drawing image.
        draw = ImageDraw.Draw(transp, "RGBA")
        draw.ellipse(xy, **kwargs)
        # Alpha composite two images together and replace first with result.
        self._cache.paste(Image.alpha_composite(self._cache, transp))

class ClickTracker(tk.BooleanVar):
    def __init__(self, cache: ImageCache, color: Color, canvas: tk.Canvas):
        """A tracker that maintains a state of whether it should track or not"""
        super(ClickTracker, self).__init__(value=True)
        self.color = color
        self.cache = cache
        self.canvas = canvas

    def track(self, x: int, y: int):
        if self.get():
            print(self.color)
            print(type(self.color))
            self.cache.ellipse(x, y, color=self.color)
            self.draw_point_on_canvas(x, y, color=Color_dict.get(self.color))


    def draw_point_on_canvas(self, x, y, color, size=5):
        x1 = x - size
        y1 = y - size
        x2 = x + size
        y2 = y + size
        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline=color)

class MoveTracker(tk.BooleanVar):
    def __init__(self, cache: ImageCache, canvas: tk.Canvas):
        """A tracker that maintains a state of whether it should track or not"""
        super(MoveTracker, self).__init__(value=True)
        self.position = None
        self.cache = cache
        self.canvas = canvas

    def track(self, x: int, y: int):
        if self.get():
            position = (x, y)
            if self.position:
                self.cache.line(start=self.position, end=position)
                self.draw_line_on_canvas(self.position, position)
            self.position = position
            
    
    def draw_line_on_canvas(self, start: Position, end: Position):
        # print(f"Start at {start[0]},{start[1]} and stop at {end[0]},{end[1]}")
        self.canvas.create_line(start[0], start[1], end[0], end[1], fill="white", width=2)

class Trackers(mouse.Listener):
    def __init__(
        self,
        click_trackers: Dict[mouse.Button, ClickTracker],
        move_tracker: MoveTracker,
    ):
        """
        Implemented by pynput.mouse
        The `mouse.Listener` will create a thread.
        """
        self.click_trackers = click_trackers
        self.move_tracker = move_tracker

    def reset(self):
        """Reset the mouse listener"""
        super(Trackers, self).__init__(
            on_move=self.move_tracker.track, on_click=self.on_click
        )

    def on_click(self, x, y, button, pressed):
        """Pick the right tracker and track"""
        if pressed:
            self.click_trackers[button].track(x, y)

class App(tk.Tk):
    def __init__(self):
        super(App, self).__init__()

        self.title("Mouse Tracker")
        self.geometry("1280x1080")

        self.start_button = Button(self, text="Start Tracking", command=self.start_tracking)

        self.stop_button = Button(self, text="Stop Tracking", command=self.stop_tracking)
        self.stop_button.switch()

        self.exit_button = Button(self, text="Exit Program", command=self.destroy)


        self.cache = ImageCache(
            size=(self.winfo_screenwidth(), self.winfo_screenheight())
        )

        self.canvas = tk.Canvas(self, width=self.winfo_screenwidth(), height=self.winfo_screenheight(), bg="black")
        self.canvas.pack()

        self.trackers = Trackers(
            click_trackers={
                mouse.Button.left: ClickTracker(cache=self.cache, color=Colors.Left, canvas=self.canvas),
                mouse.Button.middle: ClickTracker(cache=self.cache, color=Colors.Middle, canvas=self.canvas),
                mouse.Button.right: ClickTracker(cache=self.cache, color=Colors.Right, canvas=self.canvas),
            },
            move_tracker=MoveTracker(self.cache, self.canvas),
        )

        self.check_buttons = [
            Checkbutton(self, text=text, variable=tracker)
            for text, tracker in zip(
                ["Record left click position", "Record mid click position", "Record right click position", "Record mouse movements"],
                [*self.trackers.click_trackers.values(), self.trackers.move_tracker],
            )
        ]


    def start_tracking(self):
        # Start tracking
        self.start_button.switch()
        self.stop_button.switch()
        self.trackers.reset()
        self.trackers.start()

    def stop_tracking(self):
        # Stop tracking
        self.stop_button.switch()
        self.start_button.switch()
        self.cache.save()
        self.trackers.stop()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()