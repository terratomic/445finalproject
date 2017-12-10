from Tkinter import *
from tkFileDialog import askopenfilename, asksaveasfile
from PIL import ImageTk, Image, ImageDraw
import numpy as np
from pprint import pprint




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
        self.buttonsdict[button_text] = b

    def __init__(self):

        self.looking = True
        self.origin_x = None
        self.origin_y = None
        self.ground = {}

        self.end_x = None
        self.end_y = None

        self.root = Tk()

        self.buttons = []
        self.buttonsdict = {}
        self.active_button = None
        self.add_button("paint", self.paint)
        self.add_button("invert", self.invert)
        self.add_button("scissors", self.scissor)
        self.add_button("resize", self.resize)
        self.add_button("select", self.select)
        self.add_button("interest_region", self.interest_region)
        self.add_button("known_foreground", self.known_foreground)
        self.add_button("extract", self.extract)
        self.add_button("clear", self.clear)

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

    def clear(self):
        self.canvas.delete("rect")
        self.canvas.delete("interest_region")
        self.canvas.delete("known_foreground")
        self.active_button.config(relief=RAISED)
        self.active_button = None



    def down(self, event):
        self.prev_x, self.prev_y = None, None
        self.pressed = True
        if self.active_button == self.buttonsdict["select"]and self.looking:
            self.origin_x = event.x
            self.origin_y = event.y
            self.looking = False


    def up(self, event):
        self.pressed = False
        if self.active_button != self.buttonsdict["select"]:
            self.looking = True


    def on_motion(self, event):
        if not self.pressed:
            return
        x, y = event.x, event.y

        if self.active_button == self.buttons[0]:
            if self.prev_x and self.prev_y:
                self.canvas.create_line(self.prev_x, self.prev_y, x, y, width=10, fill="black", capstyle=ROUND, smooth=TRUE)
                self.draw.line([self.prev_x, self.prev_y, x, y], fill="black", width=10)
            self.prev_x, self.prev_y = x, y
        if self.active_button == self.buttonsdict["select"]:

            self.end_x = x
            self.end_y = y
            self.canvas.delete("rect")

            self.canvas.create_rectangle(self.origin_x, self.origin_y, self.end_x, self.end_y, tags="rect")


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

        self.drawImage(im)

    def scissor(self):
        print "scissor"
        pass

    def resize(self):
        print "resize"
        pass

    def select(self):
        print "select"
        pass

    def interest_region(self):
        self.storeInput("interest_region", "red")

    def known_foreground(self):
        self.storeInput("known_foreground", "green")


    def storeInput(self, groundType, color):
        self.active_button.config(relief=RAISED)
        self.active_button = None
        im = np.array(self.buf)

        #######################################################################
        # do stuff here to numpy image
        #

        temp = im[self.origin_y:self.end_y, self.origin_x:self.end_x]
        self.ground[groundType] = temp

        print groundType
        self.printVals()
        print ""
        self.canvas.create_rectangle(self.origin_x, self.origin_y, self.end_x, self.end_y, tags=groundType, outline=color)


    def printVals(self):
        print "origin"
        print self.origin_x, self.origin_y
        print "end"
        print self.end_x, self.end_y

    def extract(self):
        self.active_button.config(relief=RAISED)
        self.active_button = None

        im = np.array(self.buf)
        #######################################################################
        # do stuff here to numpy image

        pprint (im[self.origin_y:self.end_y, self.origin_x:self.end_x])
        im[self.origin_y:self.end_y, self.origin_x:self.end_x] = 255 - im[self.origin_y:self.end_y, self.origin_x:self.end_x]


        #print im
        self.drawImage(im)



    def drawImage(self, im):
        img = Image.fromarray(im, "RGB")
        self.buf = img

        self.draw = ImageDraw.Draw(self.buf)
        photo_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=photo_img, anchor="nw")
        self.canvas.img = photo_img

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
