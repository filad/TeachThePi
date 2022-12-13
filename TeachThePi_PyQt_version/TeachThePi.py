# Adam Filkor, 2022
# coding=utf-8
import sys
import time
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QThread
import picamera
import numpy as np
import tensorflow as tf
from MySqueezenet import squeezenet
import uuid
import os
from random import *
##time, misc, for testing
import time


class VideoThread(QThread):
    def __init__(self):
        super(VideoThread, self).__init__()
        self.recording = False
        self.imgClass = ''
        self.preview_x = 0
        self.preview_y = 0
        self.moved = False
        
        ##NNet
        self.config = tf.ConfigProto(log_device_placement = False)
        self.config.gpu_options.allow_growth = True
        self.config.gpu_options.allocator_type = 'BFC'           
        self.data, self.sqz_mean = squeezenet.load_net('MySqueezenet/sqz_full.mat')
        self.g = tf.Graph()
        
        self.Red_logits = []
        self.Green_logits = []
        self.Blue_logits = []
        ## distances [['Red',55], ['Red',33.4], ['Green',55], ['Blue',21]]
        self.distances = []
        self.K = 10 #k-value for KNN
        self.preds = {"Red": 0, "Green": 0, "Blue" : 0} #predictions
    

    def run(self):
        
        
        #self.setPriority(QThread.HighPriority)
        with self.g.as_default(), tf.Session(config=self.config) as sess:
            image = tf.placeholder(dtype=squeezenet.get_dtype_tf(), name="image_placeholder")
            keep_prob = tf.placeholder(squeezenet.get_dtype_tf())
            sqznet = squeezenet.net_preloaded(self.data, image, 'max', True, keep_prob)
                
            
            
            with picamera.PiCamera() as self.camera:
                self.camera.resolution = (320, 240)
                self.camera.framerate = 25
                self.camera.shutter_speed = 40000
                self.camera.start_preview(fullscreen = False, window = (132,265,420,315))
                
           
                
                while (1):
                    start = time.time()
                    
                    if self.moved == True:
                        self.camera.preview.window = (self.preview_x, self.preview_y, 420, 315)
                        self.moved = False
                    
                    if self.recording == True:
                        print('capture')
                        randString = uuid.uuid4().hex[:6] #generate random string length 6
                        imgPath =  '/home/pi/images/' + self.imgClass + '/img-' + randString +'.jpg'
                        self.camera.capture(imgPath, use_video_port = True)
                        self.emit(QtCore.SIGNAL("addToGrid(QString,QString)"), imgPath, self.imgClass)
                        file_count = len([f for f in os.listdir('/home/pi/images/' + self.imgClass)])
                        print(self.imgClass + ' file_count: ', file_count)
                        #time.sleep(0.2)
                        
                        img = squeezenet.imread_resize(imgPath)
                        if self.imgClass == "Green":
                            self.Green_logits.append(sqznet['classifier_pool'].eval(feed_dict={image: [squeezenet.preprocess(img, self.sqz_mean)], keep_prob: 1.})[0][0][0])
                            #print ('green recorded- ')
                        
                        if self.imgClass == "Blue":
                            self.Blue_logits.append(sqznet['classifier_pool'].eval(feed_dict={image: [squeezenet.preprocess(img, self.sqz_mean)], keep_prob: 1.})[0][0][0])
                            #print ('blue recorded - ')
                        if self.imgClass == "Red":
                            self.Red_logits.append(sqznet['classifier_pool'].eval(feed_dict={image: [squeezenet.preprocess(img, self.sqz_mean)], keep_prob: 1.})[0][0][0])
                            #print ('red recorded- ')
                    else:
                        ##when not recording frames
                        self.camera.capture('/home/pi/images/live.jpg', use_video_port = True)
                        liveImg = squeezenet.imread_resize('/home/pi/images/live.jpg')
                        
                        time_eval_start = time.time()
                        liveLogit = sqznet['classifier_pool'].eval(feed_dict={image: [squeezenet.preprocess(liveImg, self.sqz_mean)], keep_prob: 1.})[0][0][0]
                        end = time.time()
                        print('Time for .eval: ', end - time_eval_start)
                        
                        #calculate distances
                        for redLogit in self.Red_logits:
                            self.distances.append(['Red', np.sqrt(np.sum((liveLogit - redLogit)**2 , axis=0))])
                        for greenLogit in self.Green_logits:
                            self.distances.append(['Green', np.sqrt(np.sum((liveLogit - greenLogit)**2 , axis=0))])
                        for blueLogit in self.Blue_logits:
                            self.distances.append(['Blue', np.sqrt(np.sum((liveLogit - blueLogit)**2 , axis=0))])
                    
                    
                        #sort list of lists by the second element, növekvő
                        self.distances.sort(key = lambda x: x[1])
                        
                        for i in self.distances[0:self.K]:
                            if i[0] == "Red":
                                self.preds["Red"] += 1
                            if i[0] == "Green":
                                self.preds["Green"] += 1 
                            if i[0] == "Blue":
                                self.preds["Blue"] += 1 
                                                    
                        
                        #normalize predictions
                        self.preds["Red"] /= self.K
                        self.preds["Green"] /= self.K
                        self.preds["Blue"] /= self.K
                        
                        #print(type(liveLogit), ' ---')
                        #print('distances ', self.distances)
                        print('--preds--: ',self.preds)                        
                        
                        self.emit(QtCore.SIGNAL("predictions(float,float,float)"), self.preds["Green"], self.preds["Blue"], self.preds["Red"])
                        
                    end = time.time()
                    print('Time for one iteration: ', end - start)
                        
                    
                    #clear up
                    self.preds["Red"] = 0
                    self.preds["Green"] = 0
                    self.preds["Blue"] = 0
                    #empty the distances, FONTOS
                    del self.distances[:]
                    
                self.camera.stop_preview()
    
    def startRec(self, s):
        self.recording = True
        self.imgClass = s
        print('Start recording frames for "' + s + '" classes')
    
    def stopRec(self):
        self.recording = False
        self.imgClass = ''
    
    def clearLogits(self, c):
        #you need to clear classes from distances, too..
        if c == "Green":
            self.Green_logits = []
            self.distances = [x for x in self.distances if x[0] != "Green"] # remove Greens
            self.preds["Green"] = 0
        if c == "Blue":
            self.Blue_logits = []
            self.distances = [x for x in self.distances if x[0] != "Blue"] 
            self.preds["Blue"] = 0            
        if c == "Red":
            self.Red_logits = []
            self.distances = [x for x in self.distances if x[0] != "Red"] 
            self.preds["Red"] = 0 
            
        
    def repositionPreview(self, i, j):
        self.preview_x = i
        self.preview_y = j
        self.moved = True
        
        
class Window(QtGui.QMainWindow):
    moved = QtCore.pyqtSignal() ##need to define outside
    
    def __init__(self):
        super(Window, self).__init__()
        self.preview_x = 30
        self.preview_y = 120
        self.greenThumbsPos = {'Row': 1, 'Column': 1}
        self.blueThumbsPos = {'Row': 1, 'Column': 1}
        self.redThumbsPos = {'Row': 1, 'Column': 1}
        self.thumbSizes = {'x': 60, 'y' : 45}
        self.setGeometry(40, 80, 1150, 620)
        self.setFixedSize(1150,620)
        self.setWindowTitle("Teach The Pi")
        
        self.deleteFiles('/home/pi/images/Green')
        self.deleteFiles('/home/pi/images/Blue')
        self.deleteFiles('/home/pi/images/Red')
        self.home()
        
    def mov(self):
        #print('moved:', self.pos().x(), self.pos().y())
        self.emit(QtCore.SIGNAL("repositionPreview(int,int)"), self.pos().x(), self.pos().y())
        
        
    def moveEvent(self, event):
        self.moved.emit()
        return super(Window, self).moveEvent(event)
        
    def home(self):
        
        
        self.vidFrame = QtGui.QFrame(self)
        self.vidFrame.setFrameShape(QtGui.QFrame.Panel | QtGui.QFrame.Raised) #Panel
        self.vidFrame.setLineWidth(2);
        self.vidFrame.resize(450,350)
        self.vidFrame.move(self.preview_x, self.preview_y)
        self.vidFrame.setStyleSheet("background-color: rgb(250,250,250); border-radius: 5px; border: 5px solid #ddd;")
        
        self.videoThread = VideoThread()
        self.videoThread.start()
        
        #lehet, hogy ezt kiveszem
        #self.moved.connect(lambda: self.videoThread.repositionPreview(self.pos().x() + self.preview_x + 60, self.pos().y() + self.preview_y + 60))
        #print(self.pos().x() + self.preview_x)
        
        btn = QtGui.QPushButton("Quit", self)
        btn.clicked.connect(self.close_application)
        
        btn.resize(100, 60)
        btn.move(30, 20)
        
        #~ self.text = QtGui.QLabel("Db kép")
        #~ self.lay = QtGui.QVBoxLayout()
        #~ self.lay.addWidget(self.text)
        #self.lay.setGeometry(300, 20)
        
        self.progressGreen = QtGui.QProgressBar(self)
        self.progressGreen.setGeometry(800, 80, 250, 40)
        self.progressGreen.setValue(0)
        self.progressGreen.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                background-color: #dddddd;
                border-radius: 3px;
                color: #111;
                font-weight: bold;
                text-align: center; 
                
            }
            
            QProgressBar::chunk {
                background-color: rgb(59, 200, 24);
            }  
            """)
   
        
        self.greenBtn = QtGui.QPushButton("Train Zöld", self)
        self.greenBtn.move(800, 130)
        self.greenBtn.resize(self.greenBtn.sizeHint().width(), 40)
        #passing arguments with 'lambda: ..'
        self.greenBtn.pressed.connect(lambda: self.videoThread.startRec('Green'))
        self.greenBtn.released.connect(self.videoThread.stopRec)
        
        self.greenDelBtn = QtGui.QPushButton("Del", self)
        self.greenDelBtn.move(910, 130)
        self.greenDelBtn.resize(50, 40)
        self.greenDelBtn.clicked.connect(lambda: self.deleteFiles('/home/pi/images/Green'))
        self.greenDelBtn.clicked.connect(lambda: self.emptyLayout(self.greenThumbsGrid, "Green"))
        self.greenDelBtn.clicked.connect(lambda: self.videoThread.clearLogits("Green"))
        
        ####Blue Progress + Btn
        self.progressBlue = QtGui.QProgressBar(self)
        self.progressBlue.setGeometry(800, 250, 250, 40)
        self.progressBlue.setValue(0)
        self.progressBlue.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                background-color: #dddddd;
                border-radius: 3px;
                color: #111;
                font-weight: bold;
                text-align: center; 
                
            }
            
            QProgressBar::chunk {
                background-color: rgb(89, 171, 227);
            }  
            """)
        
        self.blueBtn = QtGui.QPushButton("Train Kék", self)
        self.blueBtn.move(800,300)
        self.blueBtn.resize(self.blueBtn.sizeHint().width(), 40)
        self.blueBtn.pressed.connect(lambda: self.videoThread.startRec('Blue'))
        self.blueBtn.released.connect(self.videoThread.stopRec)
        
        self.blueDelBtn = QtGui.QPushButton("Del", self)
        self.blueDelBtn.move(910, 300)
        self.blueDelBtn.resize(50, 40)
        self.blueDelBtn.clicked.connect(lambda: self.deleteFiles('/home/pi/images/Blue'))
        self.blueDelBtn.clicked.connect(lambda: self.emptyLayout(self.blueThumbsGrid, "Blue"))
        self.blueDelBtn.clicked.connect(lambda: self.videoThread.clearLogits("Blue"))
        
        
        
        
        self.progressRed = QtGui.QProgressBar(self)
        self.progressRed.setGeometry(800, 430, 250, 40)
        self.progressRed.setValue(0)
        self.progressRed.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                background-color: #dddddd;
                border-radius: 3px;
                color: #111;
                font-weight: bold;
                text-align: center; 
                
            }
            
            QProgressBar::chunk {
                background-color: rgb(240, 52, 52);
            }  
            """)
        
        #Red Btn
        self.redBtn = QtGui.QPushButton("Train Piros", self)
        self.redBtn.move(800,480)
        self.redBtn.resize(self.redBtn.sizeHint().width(), 40)
        self.redBtn.pressed.connect(lambda: self.videoThread.startRec('Red'))
        self.redBtn.released.connect(self.videoThread.stopRec)
        
        self.redDelBtn = QtGui.QPushButton("Del", self)
        self.redDelBtn.move(910, 480)
        self.redDelBtn.resize(50, 40)
        self.redDelBtn.clicked.connect(lambda: self.deleteFiles('/home/pi/images/Red'))
        self.redDelBtn.clicked.connect(lambda: self.emptyLayout(self.redThumbsGrid, "Red"))  
        self.redDelBtn.clicked.connect(lambda: self.videoThread.clearLogits("Red"))      
        
        
        
        ##Green Thumbs Frame and grid
        self.greenThumbsFrame = QtGui.QFrame(self)
        self.greenThumbsFrame.setFrameShape(QtGui.QFrame.Panel | QtGui.QFrame.Raised) #Panel
        self.greenThumbsFrame.setLineWidth(1);
        self.greenThumbsFrame.resize(205,160)
        self.greenThumbsFrame.move(570, 30)
        #self.greenThumbsFrame.setStyleSheet("background-color: rgb(250,240,210);")
        
        #self.widget = QtGui.QWidget() 
        self.greenThumbsGrid = QtGui.QGridLayout()
        self.greenThumbsGrid.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.greenThumbsGrid.setSpacing(1)
        #self.greenThumbsGrid.setVerticalSpacing(0)
        #self.greenThumbsGrid.setContentsMargins(0,0,0,0)
        self.greenThumbsFrame.setLayout(self.greenThumbsGrid)
        
        
        
        ################################################################
        ###Blue Thumbs Frame and grid
        self.blueThumbsFrame = QtGui.QFrame(self)
        self.blueThumbsFrame.setFrameShape(QtGui.QFrame.Panel | QtGui.QFrame.Raised) #Panel
        self.blueThumbsFrame.setLineWidth(1);
        self.blueThumbsFrame.resize(205,160)
        self.blueThumbsFrame.move(570, 210)
        #self.greenThumbsFrame.setStyleSheet("background-color: rgb(250,240,210);")
        
        #self.widget = QtGui.QWidget() 
        self.blueThumbsGrid = QtGui.QGridLayout()
        self.blueThumbsGrid.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.blueThumbsGrid.setSpacing(1)
        #self.greenThumbsGrid.setVerticalSpacing(0)
        #self.greenThumbsGrid.setContentsMargins(0,0,0,0)
        self.blueThumbsFrame.setLayout(self.blueThumbsGrid)
        
        
        
        ################################################################
        ###Red Thumbs Frame and grid
        self.redThumbsFrame = QtGui.QFrame(self)
        self.redThumbsFrame.setFrameShape(QtGui.QFrame.Panel | QtGui.QFrame.Raised) #Panel
        self.redThumbsFrame.setLineWidth(1);
        self.redThumbsFrame.resize(205,160)
        self.redThumbsFrame.move(570, 400)
        #self.redThumbsFrame.mouseReleaseEvent = lambda: self.deleteFiles('/home/pi/images/Red')
        #self.greenThumbsFrame.setStyleSheet("background-color: rgb(250,240,210);")
        
        #self.widget = QtGui.QWidget() 
        self.redThumbsGrid = QtGui.QGridLayout()
        self.redThumbsGrid.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.redThumbsGrid.setSpacing(1)
        #self.greenThumbsGrid.setVerticalSpacing(0)
        #self.greenThumbsGrid.setContentsMargins(0,0,0,0)
        self.redThumbsFrame.setLayout(self.redThumbsGrid)
        
        
        #Msg SIGNAL from Thread 
        self.connect(self.videoThread, QtCore.SIGNAL("addToGrid(QString,QString)"), self.addThumbsToGrid)
        self.connect(self.videoThread, QtCore.SIGNAL("predictions(float,float,float)"), self.updateProgressBars)
        
        #Change style to Plastique
        #QtGui.QApplication.setStyle(QtGui.QStyleFactory.create("Plastique"))
        
        
        self.show()
        
          
    def download(self):
        self.completed = 0
        while self.completed < 100:
            self.completed += 0.01
            self.progressGreen.setValue(self.completed)
            
            
    def deleteFiles(self, folder):
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            try:
                os.unlink(file_path)
            except Exception as e:
                print(e)
                
    def updateProgressBars(self, green, blue, red):
        green = green * 100
        blue = blue * 100
        red = red * 100
        ##Csak, hogy jobban nézzen ki, egy kis random zaj a százalékra
        if (green != 0):
            green = green + random()*6 - 3
        if (blue != 0):
            blue = blue + random()*6 - 3
        if (red != 0):
            red = red + random()*6 - 3
        
        self.animG = QtCore.QPropertyAnimation(self.progressGreen, "value")
        self.animG.setDuration(350)
        self.animG.setStartValue(self.progressGreen.value())
        self.animG.setEndValue(green)
        self.animG.start()
        
        self.animB = QtCore.QPropertyAnimation(self.progressBlue, "value")
        self.animB.setDuration(350)
        self.animB.setStartValue(self.progressBlue.value())
        self.animB.setEndValue(blue)
        self.animB.start()
        
        self.animR = QtCore.QPropertyAnimation(self.progressRed, "value")
        self.animR.setDuration(350)
        self.animR.setStartValue(self.progressRed.value())
        self.animR.setEndValue(red)
        self.animR.start()        
        
        #~ self.progressGreen.setValue(self.green)
        #~ self.progressBlue.setValue(blue*100)
        #~ self.progressRed.setValue(red*100)
        #~ print(self.green)
                
    def addThumbsToGrid(self, imgPath, imgClass):
        print(imgPath, imgClass)
        #3x3-at akarunk, hogy 3x3 thumbnail jelenjen meg csak
        
        if imgClass == "Green":
            
            if (self.greenThumbsPos["Row"] != 4):
                label = QtGui.QLabel('img-label', self.greenThumbsFrame)
                pixmap = QtGui.QPixmap()
                pixmap.load(imgPath)
                pixmap = pixmap.scaled(self.thumbSizes['x'],self.thumbSizes['y'], QtCore.Qt.KeepAspectRatio)
                label.setPixmap(pixmap)
                self.greenThumbsGrid.addWidget(label, self.greenThumbsPos["Row"], self.greenThumbsPos["Column"])
                
                
                    
                self.greenThumbsPos["Column"] += 1
                if (self.greenThumbsPos["Column"] % 4 == 0):
                    self.greenThumbsPos["Column"] = 1
                    self.greenThumbsPos["Row"] += 1
        
        
        if imgClass == "Blue":
            
            if (self.blueThumbsPos["Row"] != 4):
                label = QtGui.QLabel('img-label', self.blueThumbsFrame)
                pixmap = QtGui.QPixmap()
                pixmap.load(imgPath)
                pixmap = pixmap.scaled(self.thumbSizes['x'],self.thumbSizes['y'], QtCore.Qt.KeepAspectRatio)
                label.setPixmap(pixmap)
                self.blueThumbsGrid.addWidget(label, self.blueThumbsPos["Row"], self.blueThumbsPos["Column"])
                
                
                    
                self.blueThumbsPos["Column"] += 1
                if (self.blueThumbsPos["Column"] % 4 == 0):
                    self.blueThumbsPos["Column"] = 1
                    self.blueThumbsPos["Row"] += 1  
                    
        if imgClass == "Red":
            
            if (self.redThumbsPos["Row"] != 4):
                label = QtGui.QLabel('img-label', self.redThumbsFrame)
                pixmap = QtGui.QPixmap()
                pixmap.load(imgPath)
                pixmap = pixmap.scaled(self.thumbSizes['x'],self.thumbSizes['y'], QtCore.Qt.KeepAspectRatio)
                label.setPixmap(pixmap)
                self.redThumbsGrid.addWidget(label, self.redThumbsPos["Row"], self.redThumbsPos["Column"])
                
                
                    
                self.redThumbsPos["Column"] += 1
                if (self.redThumbsPos["Column"] % 4 == 0):
                    self.redThumbsPos["Column"] = 1
                    self.redThumbsPos["Row"] += 1 
        
        
        
    def emptyLayout(self, layout, imgClass):
        for i in reversed(range(layout.count())):
            layout.takeAt(i).widget().setParent(None)
            
        if imgClass == "Green":
            self.greenThumbsPos = {'Row' : 1, 'Column' : 1}
        if imgClass == "Blue":
            self.blueThumbsPos = {'Row' : 1, 'Column' : 1}
        if imgClass == "Red":
            self.redThumbsPos = {'Row' : 1, 'Column' : 1}
                
                
    def close_application(self):
        print("Closed")
        sys.exit()



def run():   
    app = QtGui.QApplication(sys.argv)
    GUI = Window()
    sys.exit(app.exec_())

run()
