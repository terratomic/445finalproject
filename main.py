from Tkinter import *
from tkFileDialog import askopenfilename, asksaveasfile
from PIL import ImageTk, Image, ImageDraw, ImageCms
from heapq import *
from pprint import pprint
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pylab
from scipy.cluster.vq import vq, kmeans, whiten
from scipy.signal import convolve2d

plt.switch_backend('Qt4Agg')
np.set_printoptions(threshold=np.nan)

WIDTH = 800
HEIGHT = 600
SEED_WIDTH = 10
dx = [0, 0, +1, -1, +1, +1, -1, -1]
dy = [+1, -1, 0, 0, -1, +1, -1, +1]
w = [1/np.sqrt(3 - dx[i]**2 - dy[i]**2) for i in range(len(dx))]
DIRS = len(dx)
OMEGA_D = 0.2
OMEGA_G = 0.8

def rgb2lab ( inputColor ) :
   num = 0
   RGB = [0, 0, 0]

   for value in inputColor :

       value = float(value) / 255

       if value > 0.04045 :
           value = ( ( value + 0.055 ) / 1.055 ) ** 2.4
       else :
           value = value / 12.92

       RGB[num] = value * 100
       num = num + 1

   XYZ = [0, 0, 0,]

   X = RGB [0] * 0.4124 + RGB [1] * 0.3576 + RGB [2] * 0.1805
   Y = RGB [0] * 0.2126 + RGB [1] * 0.7152 + RGB [2] * 0.0722
   Z = RGB [0] * 0.0193 + RGB [1] * 0.1192 + RGB [2] * 0.9505
   XYZ[ 0 ] = round( X, 4 )
   XYZ[ 1 ] = round( Y, 4 )
   XYZ[ 2 ] = round( Z, 4 )
   XYZ[ 0 ] = float( XYZ[ 0 ] ) / 95.047         # ref_X =  95.047   Observer= 2, Illuminant= D65
   XYZ[ 1 ] = float( XYZ[ 1 ] ) / 100.0          # ref_Y = 100.000
   XYZ[ 2 ] = float( XYZ[ 2 ] ) / 108.883        # ref_Z = 108.883

   num = 0
   for value in XYZ :
       if value > 0.008856 :
           value = value ** ( 0.3333333333333333 )
       else :
           value = ( 7.787 * value ) + ( 16 / 116 )

       XYZ[num] = value
       num = num + 1

   Lab = [0, 0, 0]

   L = ( 116 * XYZ[ 1 ] ) - 16
   a = 500 * ( XYZ[ 0 ] - XYZ[ 1 ] )
   b = 200 * ( XYZ[ 1 ] - XYZ[ 2 ] )

   Lab [ 0 ] = round( L, 4 )
   Lab [ 1 ] = round( a, 4 )
   Lab [ 2 ] = round( b, 4 )

   return Lab


class SubImage:
    def __init__(self, x1, y1, x2, y2, subimage, type, color):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.subimage = subimage
        self.groundType = type
        self.color = color

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
            self.reset_canvas()
            button_callback()
        b = Button(self.root, text=button_text, command=wrap_callback)
        b.grid(row = 0, column = len(self.buttons))
        self.buttons.append(b)
        self.buttonsdict[button_text] = b

    def __init__(self):
        self.images = {}
        self.canvasimages = {}
        self.canvases = {}
        self.img = None
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
        self.add_button("select", self.select)
        self.add_button("interest_region", self.interest_region)
        self.add_button("known_foreground", self.known_foreground)
        self.add_button("known_background", self.known_background)
        self.add_button("extract", self.extract)
        self.add_button("clear", self.clear)

        self.canvas = Canvas(self.root, bg="white", width=WIDTH, height=HEIGHT)
        self.canvas.grid(row=1, column=0, columnspan=len(self.buttons))
        #self.canvas.pack()

        img = Image.open("tiger.jpg")
        photo_img = ImageTk.PhotoImage(img)

        self.buf = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255)) # white
        self.draw = ImageDraw.Draw(self.buf)

        self.buf.paste(img, (0, 0))
        self.draw = ImageDraw.Draw(self.buf)
        self.render(self.buf)

        self.editor_buf = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255)) # white
        self.editor_draw = ImageDraw.Draw(self.editor_buf)

        # Scissor vars
        self.seeds = []
        self.path = []
        self.seed_x, self.seed_y = None, None
        self.path_x, self.path_y = None, None
        self.f_G = np.zeros((HEIGHT, WIDTH))
        self.f_D = np.zeros((HEIGHT, WIDTH, DIRS))

        # Paint vars
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
        self.canvas.bind('<Motion>', self.on_motion)
        self.canvas.bind('<B1-Motion>', self.on_down_motion)
        self.canvas.bind('<Button-1>', self.down)
        self.canvas.bind('<ButtonRelease-1>', self.up)
        self.root.mainloop()

    # reset canvas
    def reset_canvas(self):
        self.editor_buf = Image.fromarray(np.array(self.buf), "RGB")
        self.editor_draw = ImageDraw.Draw(self.editor_buf)
        self.render(self.editor_buf) 

    def render(self, buf):
        #self.draw = ImageDraw.Draw(self.buf)
        photo_img = ImageTk.PhotoImage(buf)
        self.canvas.create_image(0, 0, image=photo_img, anchor="nw")
        self.canvas.img = photo_img

    def dijkstras(self, f_D, f_G):
        print "dijsktras"
        start = time.time()
        q = []
        M, N = self.buf.size
        visited = np.zeros((N, M))
        self.path_x = np.zeros((N, M), dtype=np.int_)
        self.path_y = np.zeros((N, M), dtype=np.int_)
        heappush(q, (0., self.seed_x, self.seed_y, self.seed_x, self.seed_y))
        while len(q) > 0:
            cost, x, y, prev_x, prev_y = heappop(q)
            if x >= M or y >= N or x < 0 or y < 0 or visited[y, x]:
                continue
            visited[y, x] = 1
            self.path_x[y, x] = prev_x
            self.path_y[y, x] = prev_y
            for i in range(DIRS):
                x_ = x + dx[i]
                y_ = y + dy[i]
                if x_ >= M or y_ >= N or x_ < 0 or y_ < 0 or visited[y_, x_]:
                    continue
                heappush(q, (
                    cost + OMEGA_G * w[i] * f_G[y_, x_] + OMEGA_D * f_D[y, x, i],
                    x_, y_, x, y)
                )
        print "dijkstras time:", time.time() - start

    def clear(self):
        self.canvas.delete("rect")
        self.canvas.delete("interest_region")
        self.canvas.delete("known_foreground")
        self.active_button.config(relief=RAISED)
        self.active_button = None

    def down(self, event):
        self.prev_x, self.prev_y = None, None
        self.pressed = True
        if self.active_button == self.buttonsdict["paint"]:
            self.prev_x, self.prev_y = None, None
        elif self.active_button == self.buttonsdict["select"]and self.looking:
            self.origin_x = event.x
            self.origin_y = event.y
            self.looking = False
        elif self.active_button == self.buttonsdict["scissors"]:
            if not (self.seed_x == None or self.seed_y == None):
                self.editor_buf = self.scissor_buf
                self.editor_draw = self.scissor_draw
            else:
                im = np.array(self.buf)
                gy = np.array([
                   [0, -1, 0],
                   [0,  0, 0],
                   [0, +1, 0],
                ])
                gx = np.array([
                    [ 0, 0,  0],
                    [-1, 0, +1],
                    [ 0, 0,  0],
                ])
                Ix2 = np.sqrt(
                    convolve2d(im[:,:,0], gx)**2 + convolve2d(im[:,:,1], gx)**2 + convolve2d(im[:,:,2], gx)**2
                )[:HEIGHT, :WIDTH]
                Iy2 = np.sqrt(
                    convolve2d(im[:,:,0], gy)**2 + convolve2d(im[:,:,1], gy)**2 + convolve2d(im[:,:,2], gy)**2
                )[:HEIGHT, :WIDTH]
                G = np.sqrt(Ix2**2 + Iy2**2)
                self.f_G = 1 - G / np.max(G)

                Ix2 = Ix2 / (G + 0.000001)
                Iy2 = Iy2 / (G + 0.000001)

                # p current point, q neighboring point, (dx, dy) = (px - qx, py - qy)
                f_D = np.zeros((HEIGHT, WIDTH, DIRS))
                for i in range(DIRS):
                    mask = ((Iy2*dx[i] - Ix2*dy[i]) >= 0)
                    Ix2_ = np.roll(Ix2 , -dx[i], axis=1)
                    Ix2_ = np.roll(Ix2_, -dy[i], axis=0)
                    Iy2_ = np.roll(Iy2 , -dx[i], axis=1)
                    Iy2_ = np.roll(Iy2_, -dy[i], axis=0)
                    self.f_D[:, :, i] = (
                        np.arccos( # dp(p, q)
                            1 / np.sqrt(dx[i]**2 + dy[i]**2) *
                            np.abs(Iy2*dx[i] - Ix2*dy[i])
                        ) +
                        np.arccos( # dq(p, q)
                            1 / np.sqrt(dx[i]**2 + dy[i]**2) *
                            (mask * (Iy2_*dx[i] - Ix2_*dy[i]) + (1 - mask) * (-Iy2_*dx[i] + Ix2_*dy[i]))
                        )
                    ) / (3/2 * np.pi)
                    self.f_D[np.isnan(f_D)] = 100.
                
            self.seed_x, self.seed_y = event.x, event.y

            over_seed = -1
            for i, seed in enumerate(self.seeds):
                if (seed[0] - event.x)**2 + (seed[1] - event.y)**2 <= SEED_WIDTH**2:
                    over_seed = i
                    break

            self.seeds.append((self.seed_x, self.seed_y, self.path))
            if over_seed != -1: # closed the loop
                print "closed the loop"
                #boundary = np.zeros((HEIGHT, WIDTH), dtype=np.int_) 
                #path = []
                editor_arr = np.array(self.buf)
                for i, seed in enumerate(self.seeds[over_seed:]):
                    for p in seed[2]:
                        #boundary[p[1], p[0]] = 1
                        editor_arr[p[1], p[0], 0] = 255
                        editor_arr[p[1], p[0], 1] = 0
                        editor_arr[p[1], p[0], 2] = 0
                    #path.extend(seed[2])
                self.reset_canvas()
                self.render(Image.fromarray(editor_arr))
                self.seed_x, self.seed_y = None, None
                self.path = []
                self.path_x, self.path_y = None, None
                return

            self.dijkstras(self.f_D, self.f_G) 
            self.editor_draw.ellipse(
                [self.seed_x, self.seed_y, self.seed_x + SEED_WIDTH, self.seed_y + SEED_WIDTH],
                outline="red",
                fill="black"
            )
            self.render(self.editor_buf)

    def up(self, event):
        self.pressed = False
        if self.active_button != self.buttonsdict["select"]:
            self.looking = True

    def on_down_motion(self, event):
        if not self.pressed:
            return
        x, y = event.x, event.y

        if self.active_button == self.buttonsdict["paint"]:
            if self.prev_x and self.prev_y:
                self.canvas.create_line(self.prev_x, self.prev_y, x, y, width=10, fill="black", capstyle=ROUND, smooth=TRUE)
                self.draw.line([self.prev_x, self.prev_y, x, y], fill="black", width=10)
            self.prev_x, self.prev_y = x, y
        if self.active_button == self.buttonsdict["select"]:

            self.end_x = x
            self.end_y = y
            self.canvas.delete("rect")

            self.canvas.create_rectangle(self.origin_x, self.origin_y, self.end_x, self.end_y, tags="rect")
    def on_motion(self, event):
        x, y = event.x, event.y
        #print x, y, np.array(self.buf).shape
        if (
            self.active_button == self.buttons[2] and
            not (self.seed_x == None or self.seed_y == None)
        ):
            scissor_arr = np.array(self.editor_buf)

            over_seed = -1
            for i, seed in enumerate(self.seeds):
                if (seed[0] - x)**2 + (seed[1] - y)**2 <= SEED_WIDTH**2:
                    x, y, _ = seed
                    over_seed = i
                    break
            i
            cur_x, cur_y = x, y 
            self.path = []
            while not (cur_x == self.seed_x and cur_y == self.seed_y):
                #print "\t", x, y, cur_x, cur_y
                self.path.append((cur_x, cur_y))
                scissor_arr[cur_y, cur_x, 0] = 0
                scissor_arr[cur_y, cur_x, 1] = 255
                scissor_arr[cur_y, cur_x, 2] = 0
                cur_x, cur_y = self.path_x[cur_y, cur_x], self.path_y[cur_y, cur_x]
            #self.path.append((cur_x, cur_y))
            #print "\t_", x, y, cur_x, cur_y
            self.scissor_buf = Image.fromarray(scissor_arr, "RGB")
            self.scissor_draw = ImageDraw.Draw(self.scissor_buf)
            self.scissor_draw.line(
                [self.seed_x, self.seed_y, x, y],
                fill="blue",
                width = 2
            )
            self.render(self.scissor_buf)

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

    def select(self):
        print "select"
        pass

    def interest_region(self):
        self.storeInput("interest_region", "red")

    def known_foreground(self):
        self.storeInput("known_foreground", "green")

    def known_background(self):
        self.storeInput("known_background", "white")

    def storeInput(self, groundType, color):
        self.active_button.config(relief=RAISED)
        self.active_button = None
        im = np.array(self.buf)
        temp = im[self.origin_y:self.end_y, self.origin_x:self.end_x]
        sub = SubImage(self.origin_x, self.origin_y, self.end_x, self.end_y, temp, groundType, color)

        if (groundType not in self.ground):
            self.ground[groundType] = []

        self.ground[groundType].append(sub)

        self.canvas.create_rectangle(self.origin_x, self.origin_y, self.end_x, self.end_y, tags=groundType, outline=color)

    def printVals(self):
        print "origin"
        print self.origin_x, self.origin_y
        print "end"
        print self.end_x, self.end_y

    def extract(self):
        background = np.array(self.ground["known_background"][0].subimage)
        l,a,b, total, original = self.convertToLAB(background)
        # print total

        b_freqs = self.getFrequencies(total)
        # self.plot3dhist(l,a,b,1)

        foreground = np.array(self.ground["known_foreground"][0].subimage)
        l,a,b, total, original = self.convertToLAB(foreground)

        total = []
        for val in self.ground["known_foreground"]:
            interest = np.array(val.subimage)
            l,a,b,temp,original = self.convertToLAB(interest)
            total+=temp


        f_freqs = self.getFrequencies(total)

        interest = np.array(self.ground["interest_region"][0].subimage)
        l,a,b, total, original = self.convertToLAB(interest)

        original = np.array(original)
        # self.plot3dhist(l,a,b,2)

        plt.show()

        f_dist = np.inf
        b_dist = np.inf
        check1 = 0
        check2 = 0

        superoriginal = np.empty(original.shape)

        for i in range(len(original)):
            for j in range(len(original[i])):
                x,y,z = original[i][j]
                x = x/100
                y = y/100
                z = z/100
                ff = 0.0
                fb = 0.0
                try:
                    if(z in f_freqs[x][y]):
                        ff = f_freqs[x][y][z]*1.5
                except KeyError:
                    # print "KEY ERROR"
                    ff= 0.0
                fb = b_freqs[x][y][z]


                if(ff > fb or abs(fb-ff) < (3.0*10**(-5))):
                    # print "FOREGROUND"
                    superoriginal[i,j] = interest[i,j]
                    # print abs(fb-ff)
                else:

                    superoriginal[i,j] = [0,0,0]


        self.drawTriMap()

        img = Image.fromarray(superoriginal.astype(np.uint8),mode= "RGB")
        self.drawInNewWindow(img, "foreground hopefully")

        self.active_button.config(relief=RAISED)
        self.active_button = None

        self.drawInNewWindow(self.buf, "current")

    def getFrequencies(self,array):
        total = np.array(array)
        print np.shape(array)
        print "SHAPE"
        number, z = np.shape(array)

        vals = {}

        for val in total:
            x,y,z = val
            x = x/100
            y = y/100
            z = z/100
            if(x not in vals):
                vals[x] = {}
            if(y not in vals[x]):
                vals[x][y] = {}
            if(z not in vals[x][y]):
                vals[x][y][z] = 0
            vals[x][y][z] += (1.0/number)

        return vals

    def convertToLAB(self,lab):
        l = []
        a = []
        b = []
        total = []
        original = np.empty(lab.shape)
        for i in range(len(lab)):
            for j in range(len(lab[0])):
                temp1, temp2, temp3 = rgb2lab(lab[i,j])
                l.append(temp1)
                a.append(temp2)
                b.append(temp3)
                total.append([temp1, temp2, temp3])
                original[i,j,0] = temp1
                original[i,j,1] = temp2
                original[i,j,2] = temp3
        return l,a,b, total, original

    def plot3dhist(self,l,a,b,n):
        l = np.array(l)
        a = np.array(a)
        b = np.array(b)
        fig = plt.figure(n)
        # print lab[:,:,0]
        ax = Axes3D(fig)
        ax.bar(l,a,b)
        print "hi2"
        print "hi3"

    def drawTriMap(self):
        im = self.img
        im = im[:,:,0]
        im = im.astype(float)
        im[:,:] = 0.0

        back_subimage = self.ground["known_background"][0]
        interest_subimage = self.ground["interest_region"][0]
        foreground_subimage_list = self.ground["known_foreground"]

        im[back_subimage.y1:back_subimage.y2, back_subimage.x1: back_subimage.x2] = 0.0
        im[interest_subimage.y1:interest_subimage.y2, interest_subimage.x1:interest_subimage.x2] = 0.5

        for foreground_subimage in foreground_subimage_list:
            im[foreground_subimage.y1:foreground_subimage.y2, foreground_subimage.x1:foreground_subimage.x2] = 1.0

        self.trimap = im
        im = 255 * im
        img = Image.fromarray(im.astype(np.uint8),mode= "L")
        self.drawInNewWindow(img, "trimap")

    def drawInNewWindow(self, img, imageName):
        self.master = Toplevel()
        canvas = Canvas(self.master, bg="white", width=500, height=300)

        canvas.pack()

        photo_img = ImageTk.PhotoImage(img)
        canvas.create_image(0,0,image = photo_img, anchor ="nw")

        self.images[imageName] = img
        self.canvasimages[imageName] = photo_img
        self.canvases[imageName] = canvas

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
        self.img = np.array(img.convert("RGB"))
        self.raw_img = img.convert("RGB")
        self.buf.paste(img, (0, 0))
        self.draw = ImageDraw.Draw(self.buf)

if __name__ == "__main__":
    ImageEditor()
