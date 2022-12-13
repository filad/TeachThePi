# Adam Filkor 2022
import logging
import sys
import time
import socket
import threading
import queue

from picamera.array import PiRGBArray
from picamera import PiCamera

import numpy as np
import tensorflow as tf
from MySqueezenet import squeezenet


class NeuralNet (threading.Thread):
    
    def __init__(self, camera):
        threading.Thread.__init__(self)
        
        self.logger = logging.getLogger("camera")
        self.imgClass = ''
        
        #self.queue_to_android = q_android
        #self.queue_to_NN = q_NN
        
        #signaling through Events between threads
        self.recordingA = threading.Event()
        self.recordingB = threading.Event()
        
        self.camera = camera
        self.rawCapture = PiRGBArray(self.camera, size=(227, 227))
        self.stream = self.camera.capture_continuous(self.rawCapture, format="rgb", resize=(227,227), use_video_port=True)
        #camera.start_preview(fullscreen = False, window = (132,265,420,315))
        self.recorded_frames_Green = 0;
        self.recorded_frames_Blue = 0;
        
        self.recording = False
        
        ## NNet
        # intra_op_parallelism_threads=0
        self.config = tf.ConfigProto(log_device_placement = False, intra_op_parallelism_threads=0) 
        self.config.gpu_options.allow_growth = True
        self.config.gpu_options.allocator_type = 'BFC' 
                  
        self.data, self.sqz_mean = squeezenet.load_net('MySqueezenet/sqz_full.mat')
        self.g = tf.Graph()
        
        self.Red_logits = []
        self.Green_logits = []
        self.Blue_logits = []
        
        # distances examples [['Red',55], ['Red',33.4], ['Green',55], ['Blue',21]]
        self.distances = []
        self.K = 10 # k-value for KNN
        self.preds = {"Red": 0, "Green": 0, "Blue" : 0} # predictions
        
        
    def run(self):
        
        with self.g.as_default(), tf.Session(config=self.config) as sess:
            image = tf.placeholder(dtype=squeezenet.get_dtype_tf(), name="image_placeholder")
            keep_prob = tf.placeholder(squeezenet.get_dtype_tf())
            sqznet = squeezenet.net_preloaded(self.data, image, 'max', True, keep_prob)
                
                
            while (1):
                start = time.time()
                f = next(self.stream)
                frame = f.array
                self.rawCapture.truncate(0)
                
                
                if self.recordingA.isSet():
                    print('Recording trainingA image..')
                    
                    self.Green_logits.append(sqznet['classifier_pool'].eval(feed_dict={image: [squeezenet.preprocess(frame, self.sqz_mean)], keep_prob: 1.})[0][0][0])
                    
                    #We will send back the number of recorded frames, it's not necessary, but a good information for the Android client.  
                    self.recorded_frames_Green += 1
                
                elif self.recordingB.isSet():
                    print('Recording trainingB image..')
                    
                    self.Blue_logits.append(sqznet['classifier_pool'].eval(feed_dict={image: [squeezenet.preprocess(frame, self.sqz_mean)], keep_prob: 1.})[0][0][0])
                    self.recorded_frames_Blue += 1
                    
                else:

                    time_eval_start = time.time()
                    liveLogit = sqznet['classifier_pool'].eval(feed_dict={image: [squeezenet.preprocess(frame, self.sqz_mean)], keep_prob: 1.})[0][0][0]
                    end = time.time()
                    print('Time for .eval: ', end - time_eval_start)
                     
                    
                    # calculate distances
                    for redLogit in self.Red_logits:
                        self.distances.append(['Red', np.sqrt(np.sum((liveLogit - redLogit)**2 , axis=0))])
                    for greenLogit in self.Green_logits:
                        self.distances.append(['Green', np.sqrt(np.sum((liveLogit - greenLogit)**2 , axis=0))])
                    for blueLogit in self.Blue_logits:
                        self.distances.append(['Blue', np.sqrt(np.sum((liveLogit - blueLogit)**2 , axis=0))])
                
                
                    # sort list of lists by the second element, ascentind
                    self.distances.sort(key = lambda x: x[1])
                    
                    for i in self.distances[0:self.K]:
                        if i[0] == "Red":
                            self.preds["Red"] += 1
                        if i[0] == "Green":
                            self.preds["Green"] += 1 
                        if i[0] == "Blue":
                            self.preds["Blue"] += 1 
                                                
                    # normalize predictions
                    self.preds["Red"] /= self.K
                    self.preds["Green"] /= self.K
                    self.preds["Blue"] /= self.K
                    
                    print('--preds--: ',self.preds)                        
                    
                                            
                end = time.time()
                print('Time for one iteration: ', end - start)
                        
                # clear up
                self.preds["Red"] = 0
                self.preds["Green"] = 0
                self.preds["Blue"] = 0
                
                # empty the distances, FONTOS
                del self.distances[:]
                
                

            self.stream.close()
            self.rawCapture.close()
            self.camera.close()
        
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
            self.recorded_frames_Green = 0
        if c == "Blue":
            self.Blue_logits = []
            self.distances = [x for x in self.distances if x[0] != "Blue"] 
            self.preds["Blue"] = 0  
            self.recorded_frames_Blue = 0          
        if c == "Red":
            self.Red_logits = []
            self.distances = [x for x in self.distances if x[0] != "Red"] 
