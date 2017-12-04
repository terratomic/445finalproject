from Tkinter import *
from tkFileDialog import askopenfilename, asksaveasfile
from PIL import ImageTk, Image, ImageDraw
import numpy as np

class ImageEditor:

    def add_button(self, button_text, button_callback):
        b = None
        def wrap_callback():
            if self.active_button == b:
                return
            if self.active_button:
                self.active_button.config(relief=RAISED)
            b.config(relief=SUNKEN) 
            self.active_button = b
            button_callback()
        b = Button(self.root, text=button_text, command=wrap_callback)
        b.grid(row = 0, column = len(self.buttons))
        self.buttons.append(b)

    def __init__(self):
        self.root = Tk()

        self.buttons = []
        self.active_button = None
        self.add_button("paint", self.paint)
        self.add_button("invert", self.invert)
        self.add_button("scissors", self.scissor)
        self.add_button("resize", self.resize)

        self.canvas = Canvas(self.root, bg="white", width=500, height=300)
        self.canvas.grid(row=1, column=0, columnspan=len(self.buttons))
        #self.canvas.pack()

        self.buf = Image.new("RGB", (500, 300), (255, 255, 255)) # white
        self.draw = ImageDraw.Draw(self.buf)

        self.prev_x, self.prev_y = None, None
        self.pressed = False

        menubar = Menu(self.root)
        filemenu = Menu(menubar)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        self.root.config(menu=menubar)
        self.root.bind('<B1-Motion>', self.on_motion)
        self.root.bind('<Button-1>', self.down)
        self.root.bind('<ButtonRelease-1>', self.up)
        self.root.mainloop()

    def down(self, event):
        self.prev_x, self.prev_y = None, None
        self.pressed = True

    def up(self, event):
        self.pressed = False

    def on_motion(self, event):
        if not self.pressed:
            return
        x, y = event.x, event.y
        if self.active_button == self.buttons[0]:
            #point = self.canvas.create_oval(x, y, x+5, y+5, fill="black")
            if self.prev_x and self.prev_y:
                self.canvas.create_line(self.prev_x, self.prev_y, x, y, width=10, fill="black", capstyle=ROUND, smooth=TRUE)
                self.draw.line([self.prev_x, self.prev_y, x, y], fill="black", width=10)
            self.prev_x, self.prev_y = x, y


    def paint(self):
        print "paint"
        pass

    def invert(self):
        print "invert"
        self.active_button.config(relief=RAISED)
        self.active_button = None
        im = np.array(self.buf)

        #######################################################################
        # do stuff here to numpy image
        #
        im = 255 - im

        img = Image.fromarray(im, "RGB")
        self.buf = img
        self.draw = ImageDraw.Draw(self.buf)
        photo_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=photo_img, anchor="nw")
        self.canvas.img = photo_img

    def scissor(self):
        print "scissor"
        pass

    def resize(self):
        print "resize"
        pass


    def save_file(self):
        fname = asksaveasfile(mode="w", defaultextension=".jpg")
        self.buf.save(fname)

    def open_file(self):
        fname = askopenfilename(filetypes=[
            ("Images", ("*.jpg", "*.gif", "*.png")),
            ("All Files", "*.*")
        ])
        
        img = Image.open(fname)
        photo_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=photo_img, anchor="nw")
        self.canvas.opened_img = photo_img

        self.buf.paste(img, (0, 0))
        self.draw = ImageDraw.Draw(self.buf)

if __name__ == "__main__":
    ImageEditor() 
