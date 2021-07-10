from sys import argv, exit
import time
import numpy as np
from PyQt4 import QtGui, QtCore
from vispy import gloo, app, use, scene
from vispy.visuals.transforms import STTransform, MatrixTransform, PolarTransform
from vispy.scene.visuals import Image, ColorBar, Markers, Text
use('pyqt4')  # can be another app backend name
import pyart
nwsref = pyart.graph.cm.NWSRef


class PTransform(PolarTransform):
    """ GL PROGRAM """
    glsl_imap = """
        vec4 polar_transform_map(vec4 pos) {
            float theta = atan(radians(pos.x), radians(pos.y));
            theta = degrees(theta + 3.14159265358979323846);
            float r = length(pos.xy);
            return vec4(r, theta, pos.z, 1);
        }
        """

class PolarImage(Image):
    # Polar Image
    def __init__(self, source=None, **kwargs):
        super(PolarImage, self).__init__(**kwargs)

        self.unfreeze()

        # source should be an object, which contains information about
        # a specific radar source
        self.source = source

        # source should contain the radar coordinates in some usable format
        # here I assume offset from lower left (0,0)
        if source is not None:
            xoff = source['X']
            yoff = source['Y']
        else:
            xoff = 0
            yoff = 0

        # this takes the image sizes and uses it for transformation
        self.theta = self._data.shape[0]
        self.range = self._data.shape[1]
        print ("Theta: ", self.theta)
        print ("Range: ", self.range)

        # PTransform takes care of making PPI from data array
        # rot rotates the ppi 180 deg (image origin is upper left)
        # the translation moves the image to centere the ppi
        rot = MatrixTransform()
        rot.rotate(180, (0, 0, 1))
        #self.transform = (
        #                  rot *
        #                  PTransform())
        self.transform = (STTransform(scale=(1.0, 1.0, 1), ))
        """
                            (STTransform(translate=(self.range+xoff, self.range+yoff, 0)) *
                          rot *
                          PTransform())
        """
        self.freeze()


class PlotWindow(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(PlotWindow, self).__init__()
        self.canvas = scene.SceneCanvas(keys=None, size=(1500,800), show=False)
        self.canvas.title = 'Plotting APP'
        self.noofbins = 633
        self.noofrays = 1
        self.running = False
        self.rayno = 0
        self.flag = 0
        self.d_rayno = 0
        self.rText = None
        self.cmap_list = [
                            "viridis",
                            "cubehelix", "single_hue","hsl","husl","diverging","RdYeBuCy",
                            "autumn",
                            "blues",
                            "cool",
                            "greens",
                            "reds",
                            "spring","summer","fire","grays","hot","ice","winter","light_blues","orange","coolwarm","PuGr","GrBu","GrBu_d","RdBu"]
        self.cmap = self.cmap_list[3]
        self.actual_d = self.readdata("zpp1.csv")#gen_image(500, 500)
        self.addAxes()
        #self.initData()
        self.initPlot()
        self.initTimer()
        #self.startTimer()
        #d = np.random.normal(size=(250, 250), scale=200)

    def initPlot(self):
        #print "initPlot"
        interpolation="nearest"
        # add a line plot inside the viewbox
        #self.img_data = self.initData()
        self.img_data1 = np.ones((30,120))
        self.img_data1[1:-1,1:-1] = 40

        self.image2 = PolarImage(source=None,
                                data=self.img_data1,
                                polar=("cw", "N", "UL"),
                                method='impostor',
                                interpolation='nearest',
                                cmap=self.cmap,
                                clim=(-65, 40),
                                parent=self.viewbox.scene)

    def addAxes(self):
        #print " add some axes"
        self.grid = self.canvas.central_widget.add_grid(spacing=0,margin=5)
        self.viewbox = self.grid.add_view(row=0, col=1, camera="panzoom")
        #print dir(self.viewbox.camera.zoom)
        #print "Zoom:",self.viewbox.camera.zoom
        #print "Zoom Factor:",self.viewbox.camera.zoom_factor
        #self.viewbox.camera.zoom_factor = 0
        #print "Zoom Factor:",self.viewbox.camera.zoom_factor
        #print dir(self.viewbox.camera.zoom_factor)

        self.x_axis = scene.AxisWidget(axis_label="X axis",orientation='bottom')
        self.x_axis.stretch = (1, 0.1)
        self.grid.add_widget(self.x_axis, row=1, col=1)
        self.grid.padding = 0

        self.x_axis.link_view(self.viewbox)
        self.y_axis = scene.AxisWidget(axis_label="Y axis",orientation='left')
        self.y_axis.stretch = (0.1, 1)
        self.grid.add_widget(self.y_axis, row=0, col=0)
        self.y_axis.link_view(self.viewbox)

        self.cbar = scene.ColorBarWidget(cmap=self.cmap,clim=(-65,40),orientation='right',label_color="white",padding=(0.1,0.1))
        self.cbar.stretch = (0.1, 1)
        self.grid.padding = 0
        self.grid.add_widget(self.cbar, row=0, col=2)
        self.viewbox.events.mouse_press.connect(self.mouseclick)
        #self.cbar.link_view(self.viewbox)

    def mouseclick(self,ev):
        print ("mouseclick: ",ev.mouse_event.pos)

    def readdata(self,vptfile):
        #print """Read and validate CSV File"""
        try:
            global mask
            C = np.genfromtxt(vptfile,dtype="float",delimiter=",")
            C[C== -1 * 32768] = 0
            C = np.ma.masked_where(C <= -65, C)
            mask = np.ones(C.shape,dtype=bool)
            D = np.ma.MaskedArray(C,mask=mask)
            return D.transpose()
        except ValueError:
            print ("Invalid CSV File!!")
        except IOError:
            print ("File not found!!")
        return np.array([])

    def initData(self):
        i = 0
        #for each in self.actual_d:
            #print i, each
            #i+=1
        C=self.actual_d#[:,120]
        print ("iniData",C.shape )
        return C




    def updatePlot(self,event):
        ##print "updatePlot"
        #time.sleep(0.1)
        #print self.img_data.shape, np.array([self.actual_d[:,:self.rayno]]).transpose().shape
        #np.append(self.img_data, np.array([self.actual_d[:,:self.rayno]]).transpose(), axis=1)#self.img_data[:,:self.rayno] = self.actual_d[:,:self.rayno]
        #print self.rDate, self.rayno, self.img_data[:,:5]
        print ("D_RAYNO: ",self.d_rayno, self.rayno)
        if self.rayno >= self.noofrays:
            self.d_rayno = self.rayno%120 # 120 is the no of data available.
            self.img_data = np.concatenate((self.img_data, np.array([self.actual_d[:,self.d_rayno]]).T), axis=1)

        else:
            self.img_data[:,self.rayno] = self.actual_d[:,self.rayno]
            #print np.array([self.actual_d[:,self.rayno]]).T.shape
        #if self.rayno%100 == 0 and self.rayno!=0:
        #    print "-"*100
        #    self.viewbox.camera.set_range(x=[self.rayno-20,self.rayno+100])
        #print "PLOT SHAPE: ", self.img_data.shape
        print ("Mouse event: ",self.viewbox.camera.viewbox_mouse_event(event))
        self.rText.setText("<b>Data No.: " + str(self.rayno) +"</b>")
        self.rayno+=1
        #self.img.set_data(self.img_data)
        self.img_data1 = np.ones((30,120))
        if self.flag%2:
            self.img_data1[1:-1,1:-1] = -60
        else:
            self.img_data1[1:-1,1:-1] = 40
        self.flag += 1

        self.img.set_data(self.img_data1)
        self.viewbox.camera.set_range()
        self.canvas.update()
        ##print dir(self.parent)


    def initTimer(self):
        #print "initTimer"
        self.timer = app.Timer()
        self.timer.connect(self.updatePlot)
        #app.run()

    def startTimer(self, *args):
        #print "startTimer"
        self.timer.start(0.3)
        #print "startTimer"
        pass

    def stopTimer(self, *args):
        #print "startTimer"
        self.timer.stop()
        #print "startTimer"

    def start_stop(self, *args):
        if self.running:
            self.running=False
            self.timer.stop()
        else:
            self.running=True
            self.timer.start(0)

    def on_close(self, event):
        print('closing!')

    def on_resize(self, event):
        print('Resize %r' % (event.size, ))

    def on_key_press(self, event):
        modifiers = [key.name for key in event.modifiers]
        print('Key pressed - text: %r, key: %s, modifiers: %r' % (
            event.text, event.key.name, modifiers))

    def on_key_release(self, event):
        modifiers = [key.name for key in event.modifiers]
        print('Key released - text: %r, key: %s, modifiers: %r' % (
            event.text, event.key.name, modifiers))

    def on_mouse_press(self, event):
        self.print_mouse_event(event, 'Mouse press')

    def on_mouse_release(self, event):
        self.print_mouse_event(event, 'Mouse release')

    def on_mouse_move(self, event):
        self.print_mouse_event(event, 'Mouse move')

    def on_mouse_wheel(self, event):
        self.print_mouse_event(event, 'Mouse wheel')

    def print_mouse_event(self, event, what):
        modifiers = ', '.join([key.name for key in event.modifiers])
        print('%s - pos: %r, button: %s, modifiers: %s, delta: %r' %
              (what, event.pos, event.button, modifiers, event.delta))

    def on_draw(self, event):
        #print "on_draw"
        gloo.clear(color=True, depth=True)



class PlotApp(QtGui.QMainWindow):
    
    def __init__(self):
        super(PlotApp, self).__init__()
        
        self.initUI()
        
        
    def initUI(self):               
        
        self.main_widget = QtGui.QWidget(self)
        #l = QtGui.QHBoxLayout(self.plot_canvas.canvas.native)
        self.lbox = QtGui.QHBoxLayout(self.main_widget)#
        self.rbox = QtGui.QVBoxLayout()

        self.plot_canvas= PlotWindow(parent=self)#keys='interactive', size=(1200,800), show=False)
        #textEdit = QtGui.QTextEdit()
        self.plot_canvas.canvas.create_native()
        #self.plot_canvas.canvas.native.setParent(self)
        self.lbox.addWidget(self.plot_canvas.canvas.native)
        self.setCentralWidget(self.main_widget)

        #print plot_canvas.canvas

        self.exitAction = QtGui.QAction('Exit', self,checkable=False,toolTip="Exit (Ctrl+Q)")
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.setStatusTip('Exit application')
        self.exitAction.triggered.connect(self.close)

        self.ssAction = QtGui.QAction('Start', self,checkable=False,toolTip="Click to Start Plot")
        self.ssAction.triggered.connect(self.StartPlot)

        self.stopAction = QtGui.QAction('Stop', self,checkable=False,toolTip="Click to Stop Plot")
        self.stopAction.triggered.connect(self.StopPlot)
        self.stopAction.setDisabled(True)

        self.statusBar()

        self.menubar = self.menuBar()
        self.fileMenu = self.menubar.addMenu('&File')
        self.fileMenu.addAction(self.exitAction)

        self.action_menu = self.menubar.addMenu('&Action')
        self.action_menu.addAction(self.ssAction)
        self.action_menu.addAction(self.stopAction)

        self.toolbar = self.addToolBar('Exit')
        #toolbar.addAction(exitAction)
        self.toolbar.addAction(self.ssAction)
        self.toolbar.addAction(self.stopAction)



        self.rDate = QtGui.QLabel("<b>Data No:</b>")
        self.plot_canvas.rText = self.rDate
        #print dir(self.rDate)
        self.rbox.addWidget(self.rDate)

        self.lbox.addLayout(self.rbox)
        
        self.setGeometry(100, 100, 1800, 1200)
        self.setWindowTitle('PLOT APP')
        self.setWindowIcon(QtGui.QIcon('cloud.png'))
        self.show()
        app.run()
        #app.timer.start()
    
    def StartPlot(self):
        #self.rDate.setText("<b>Started</b>")
        self.stopAction.setDisabled(False)
        self.ssAction.setDisabled(True)
        self.plot_canvas.startTimer()

    def StopPlot(self):
        #self.rDate.setText("<b>Stopped</b>")
        self.stopAction.setDisabled(True)
        self.ssAction.setDisabled(False)
        self.plot_canvas.stopTimer()

    def UpdateDataNo(self):
        pass

        
def main():
    app1 = QtGui.QApplication(argv)
    ex = PlotApp()
    exit(app.quit())

class ShowDataTable(QtCore.QAbstractTableModel):
    def __init__(self, datain, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = datain

    def rowCount(self, parent):
        return len(self.arraydata)

    def columnCount(self, parent):
        return len(self.arraydata[0])

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        elif role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        return QtCore.QVariant(self.arraydata[index.row()][index.column()])


if __name__ == '__main__':
    main()
